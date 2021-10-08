#!/usr/bin/python3

# Program to install my usual environment on a freshly-installed Raspian

# use ifconfig to get the address

# curl https://raw.githubusercontent.com/hillwithsmallfields/JCGS-scripts/master/pi-setup.py | sudo python3 - --config https://raw.githubusercontent.com/hillwithsmallfields/JCGS-config/master/pi-setup-config.json --host shtogu

import argparse
import getpass
import glob
import json
import os
import pwd
import re
import requests
import shutil
import socket
import sys

configuration = {
    'apt-packages': [
        "emacs"
    ],
    'pip-packages': [
        "pycrypto",
        "python-decouple",
        "pyyaml",
        "sexpdata"
    ],
    'dot-files': ["emacs",
                  "bashrc",
                  "bash_profile"],
    'ext-drive': "/dev/sda1",
    'mount-point': "/mnt/hdd0",
    'projects-directory': "open-projects/github.com/hillwithsmallfields",
    'config-project': "JCGS-config",
    'github-list': "https://api.github.com/users/hillwithsmallfields/repos"
}

MODEL_FILENAME = "/proc/device-tree/model"

def file_has_line_starting(filename, incipit):
    with open(filename, 'r') as stream:
        return any((line.startswith(incipit) for line in stream))

def append_if_missing(filename, incipit, addendum):
    if not file_has_line_starting(filename, incipit):
        with open(filename, 'a') as contents:
            contents.write(addendum)

def model():
    # https://gist.github.com/jperkin/c37a574379ef71e339361954be96be12
    # yields these (after the transformations we do):
    #
    # 2-Model-B
    # 3-Model-B
    # 3-Model-B Plus
    # 4-Model-B
    # Compute-Module
    # Compute-Module-3
    # Compute-Module-3-Plus
    # Model-B
    # Model-B Plus
    # Zero-W
    #
    if os.path.isfile(MODEL_FILENAME):
        with open(MODEL_FILENAME) as model_stream:
            model_string = model_stream.read()
            found = re.search("Raspberry Pi (.+)( Rev.+ )?", model_string)
            return found.group(1).replace(' ', '-') if found else "unknown"
    else:
        return "not-a-pi"

def set_hostname(newname):
    with open("/etc/hostname", 'w') as namestream:
        namestream.write(newname + '\n')
    oldname = socket.gethostname()
    if newname != oldname:
        with open("/etc/hosts", 'r') as hoststream:
            hosts = [host.replace(oldname, newname) for host in hoststream]
        with open("/etc/hosts", 'w') as hoststream:
            for host in hosts:
                hoststream.write(host)

def add_user(user):
    """Add the user (if not already present), with their password
    disabled but ssh login allowed.
    Also put them in /etc/sudoers."""
    if user and user == "":
        print("No user specified")
        return None
    try:
        _ = pwd.getpwnam(user)
    except KeyError:
        sh('adduser --disabled-password --gecos "%s" %s' % (configuration['name'], user))
    print("run 'sudo passwd %s' to set your password" % user)
    print("then on desktop, do this: ssh-copy-id %s@%s" % (user, configuration['host']))

    sh("ssh-keygen -A && update-rc.d ssh enable && invoke-rc.d ssh start") # from the insides of raspi-config

    append_if_missing("/etc/sudoers",
                      user,
                      "%s    ALL=(ALL:ALL) ALL\n" % user)
    return user

def sh(command):
    print("Running command", command)
    os.system(command)

def main():

    if getpass.getuser() != 'root':
        print("This program must be run as root")
        sys.exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument("--user")
    parser.add_argument("--name")
    parser.add_argument("--host")
    parser.add_argument("--ext-drive")
    parser.add_argument("--mount-point")
    parser.add_argument("--configuration",
                        help="""Filename or URL (JSON) overriding built-in settings.
                        Command line --user, --name, and --host override this file.
                        If the string has % in it, the model of the Pi is substituted.
                        Use %.1s to get a single digit or Z for Zero or C for
                        Compute Module or M for the original model.""")
    args = parser.parse_args()

    global configuration
    if args.configuration:
        confname = args.configuration
        if '%' in confname:
            confname %= model()
        if confname.startswith("https://") or confname.startswith("http://"):
            configuration = requests.get(confname).json()
        else:
            with open(confname) as confstream:
                configuration = json.load(confstream)

    for k, v in vars(args).items():
        if v:
            configuration[k] = v

    if configuration.get('host', "") != "":
        set_hostname(configuration['host'])

    hostname = socket.gethostname()
    hostaddr = socket.gethostbyname(hostname)

    print("Running on host", hostname, "at address", hostaddr)

    for package in configuration['apt-packages']:
        sh("apt-get install --assume-yes %s" % package)
    for package in configuration['pip-packages']:
        sh("pip3 install %s" % package)

    user = add_user(configuration.get('user'))
    home_directory = os.path.join("/home", user)

    # If there is an external disk attached, put it where I want it:
    ext_disk = configuration.get('ext-drive')
    mount_point = configuration.get('mount-point')

    if ext_disk and os.path.exists(ext_disk) and mount_point:
        print("Moving", ext_disk, "to mount point", mount_point)
        sh("umount " + ext_disk)
        append_if_missing("/etc/fstab",
                          ext_disk,
                          "%s %s ext4 defaults 0 0\n" % (ext_disk, mount_point))
        os.makedirs(mount_point, 0o777, True)
        sh("mount " + ext_disk)
        if os.path.isdir(mount_point):
            user_dir = os.path.join(mount_point, "home", user)
            if os.path.isdir(user_dir):
                print("Linking user files from HDD")
                for filename in glob.glob(user_dir+"/*"):
                    os.symlink(os.path.join(home_directory, os.path.basename(filename)), filename)

    # Do the rest as the new user
    if user:
        print("Doing rest of setup as", user)
        os.setuid(pwd.getpwnam(user)[2])

    projects_dir_name = configuration.get('projects-directory')
    if projects_dir_name:
        projects_dir = os.path.join(home_directory, projects_dir_name)
        os.makedirs(projects_dir)
        os.chdir(projects_dir)
        print("Cloning projects into", projects_dir)
        for repo in requests.get(configuration['github-list']).json():
            if os.path.isdir(os.path.join(projects_dir, repo['name'])):
                print("Already got", repo['name'])
            else:
                sh("git clone " + repo['git_url'])

        # Now copy my dotfiles into place:
        dot_files = configuration.get('dot-files')
        config_project = configuration.get('config-project')
        if dot_files and config_project:
            config_dir = os.path.join(projects_dir, config_project)
            for dot_file in dot_files:
                origin = os.path.join(config_dir, dot_file)
                if os.path.isfile(origin):
                    shutil.copy(origin,
                                os.path.join(home_directory, "." + dot_file))

if __name__ == "__main__":
    main()
