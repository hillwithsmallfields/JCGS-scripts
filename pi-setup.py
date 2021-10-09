#!/usr/bin/python3

# Program to install my usual environment on a freshly-installed Raspian

# use ifconfig to get the address

# curl https://raw.githubusercontent.com/hillwithsmallfields/JCGS-scripts/master/pi-setup.py | sudo python3 - --default-config --host shtogu

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
    'git-repos': [],
    'repos-directory': "$HOME/open-projects",
    'ext-drive': "/dev/sda1",
    'mount-point': "/mnt/hdd0",
    'projects-directory': "open-projects/github.com/hillwithsmallfields",
    'config-project': "JCGS-config",
    'github-list': "https://api.github.com/users/hillwithsmallfields/repos"
}

dirmask = 0o777

MODEL_FILENAME = "/proc/device-tree/model"

def file_has_line_starting(filename, incipit):
    with open(filename, 'r') as stream:
        return any((line.startswith(incipit) for line in stream))

def append_to_file_if_missing(filename, incipit, addendum):
    if not file_has_line_starting(filename, incipit):
        with open(filename, 'a') as contents:
            contents.write(addendum)

def append_to_line_starting(filename, incipit, addendum):
    with open(filename, 'r') as stream:
        lines = [line for line in stream]
    with open(filename, 'w') as stream:
        for line in lines:
            if line.startswith(incipit):
                line = line[:-1] + addendum + line[-1]
            stream.write(line)

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
            found = re.search("Raspberry Pi (.+)( Rev.+ )?", model_stream.read())
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

    append_to_file_if_missing("/etc/sudoers",
                              user,
                              "%s    ALL=(ALL:ALL) ALL\n" % user)

    append_to_line_starting("/etc/group",
                            "gpio",
                            "," + user)

    return user

def sh(command):
    print("Running command", command)
    os.system(command)

def main():

    if getpass.getuser() != 'root':
        print("This program must be run as root")
        sys.exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument("--user",
                        help="""The account name of the user to create.""")
    parser.add_argument("--name",
                        help="""The full name of the user.""")
    parser.add_argument("--host",
                        help="""The name to give the host.""")
    parser.add_argument("--ext-drive",
                        help="""The expected name of an external drive.""")
    parser.add_argument("--mount-point",
                        help="""The mount point to place the external drive at,
                        if there is one.""")
    parser.add_argument("--configuration",
                        help="""Filename or URL (JSON) overriding built-in settings.
                        Command line --user, --name, and --host override this file.
                        If the string has % in it, the model of the Pi is substituted.
                        Use %.1s to get a single digit or Z for Zero or C for
                        Compute Module or M for the original model.""")
    parser.add_argument("--default-config",
                        action='store_true',
                        help="""Use a standard configuration file.""")
    parser.add_argument("--auto-config",
                        action='store_true',
                        help="""Use a standard configuration file which is different
                        for each model of Pi.""")
    args = parser.parse_args()

    global configuration

    confname = ("https://raw.githubusercontent.com/hillwithsmallfields/JCGS-config/master/pi-setup-config.json"
                if args.default_config
                else ("https://raw.githubusercontent.com/hillwithsmallfields/JCGS-config/master/pi-%.1s-setup-config.json"
                      if args.auto_config
                      else (args.configuration
                            if args.configuration
                            else None)))

    if confname:
        if '%' in confname:
            confname %= model()
        if confname.split(':', 1)[0] in ('https', 'http'):
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
    print("Using", home_directory, "as home directory")

    # If there is an external disk attached, put it where I want it:
    ext_disk = configuration.get('ext-drive')
    mount_point = configuration.get('mount-point')

    if ext_disk and os.path.exists(ext_disk) and mount_point:
        print("Moving", ext_disk, "to mount point", mount_point)
        sh("umount " + ext_disk)
        append_to_file_if_missing("/etc/fstab",
                                  ext_disk,
                                  "%s %s ext4 defaults 0 0\n" % (ext_disk, mount_point))
        os.makedirs(mount_point, dirmask, True)
        sh("mount " + ext_disk)
        if os.path.isdir(mount_point):
            user_dir = os.path.join(mount_point, "home", user)
            if os.path.isdir(user_dir):
                print("Linking user files in", user_dir, "from HDD")
                for filename in glob.glob(user_dir+"/*"):
                    link = os.path.join(home_directory, os.path.basename(filename))
                    print("  Linking", link, "to", filename)
                    os.symlink(filename, link)
        else:
            print("No directory found at mount point", mount_point)
    else:
        print("No external disk found")

    # Do the rest as the new user
    if user:
        udata = pwd.getpwnam(user)
        uid = udata[2]
        gid = udata[3]
        print("Doing rest of setup as user %s (uid %d, gid %d)"% (user, uid, gid))
        os.setgid(gid)          # can't do this after the setuid, because of not being root any longer
        os.setuid(uid)
        # os.seteuid(uid)
        # os.setegid(gid)
    else:
        print("User not specified, so completing setup as root")

    # This should be relative to the user's home directory, or absolute
    # (avoiding any confusing about using $HOME as this program runs as
    # root until it changes uid).
    projects_dir_name = configuration.get('projects-directory')
    if projects_dir_name:
        projects_dir = (projects_dir_name
                        if projects_dir_name.startswith('/')
                        else os.path.join(home_directory, projects_dir_name))
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

    repos = configuration.get('git-repos')
    # This should be relative to the user's home directory, or absolute
    # (avoiding any confusing about using $HOME as this program runs as
    # root until it changes uid).
    repos_dir_name = configuration.get('repos-directory')
    repos_directory = (repos_dir_name
                       if repos_dir_name.startswith('/')
                       else os.path.join(home_directory, repos_dir_name))

    if repos and repos_directory:
        repos_directory = os.path.expandvars(repos_directory)
        print("Fetching %s into %s", repos, repos_directory)
        for repo in repos:
            # assuming github-style naming:
            repo_name_parts = repo.split("/")
            author = "/".join(repo_name_parts[3:-1]) # from after the host to before the repo filename
            author_directory = os.path.join(repos_directory, author)
            os.makedirs(author_directory, dirmask, True)
            os.chdir(author_directory)
            print("cloning", repo, "under author directory", author_directory)
            sh("git clone " + repo)

if __name__ == "__main__":
    main()
