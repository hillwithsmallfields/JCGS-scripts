#!/usr/bin/python3

# use ifconfig to get the address

# curl -o pi-setup.py https://raw.githubusercontent.com/hillwithsmallfields/JCGS-scripts/master/pi-setup.py && chmod a+x pi-setup.py && sudo ./pi-setup.py --config https://raw.githubusercontent.com/hillwithsmallfields/JCGS-config/master/pi-setup-config.json

import argparse
import getpass
import glob
import json
import os
import pwd
import re
import requests
import shutil
import sys

configuration = {
    'apt_packages': [
        "emacs"
    ],
    'pip_packages': [
        "measurement",
        "ordered_set",
        "oura",
        "overpass2",
        "pycrypto",
        "python-decouple",
        "pyyaml",
        "sexpdata",
        "webpy"
    ],
    'dot_files': ["emacs",
                  "bashrc",
                  "bash_profile"]}

MODEL_FILENAME = "/sys/firmware/devicetree/base/model"
MY_PROJECTS_DIRECTORY="open-projects/github.com/hillwithsmallfields"
MY_CONFIG_PROJECT="JCGS-config"
MY_GITHUB_LIST="https://api.github.com/users/hillwithsmallfields/repos"

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
    if os.path.isfile("/proc/device-tree/model"):
        with open("/proc/device-tree/model") as model_stream:
            model_string = model_stream.read()
            found = re.search("Raspberry Pi (.+)( Rev.+ )?", model_string)
            return found.group(1).replace(' ', '-') if found else "unknown"
    else:
        return "not-a-pi"

def sh(command):
    print("Running command", command)
    os.system(command)

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--user")
    parser.add_argument("--name")
    parser.add_argument("--host")
    parser.add_argument("--configuration",
                        help="""Filename or URL (JSON) overriding built-in settings.
                        Command line --user, --name, and --host override this file.
                        If the string has % in it, the model of the Pi is substituted.
                        Use %.1s to get a single digit or Z for Zero or C for 
                        Compute Module or M for the original model.""")
    args = parser.parse_args()

    if args.configuration:
        if '%' in configuration:
            configuration %= model()
        if args.configuration.startswith("https://") or args.configuration.startswith("http://"):
            configuration = requests.get(configuration).json()
        else:
            with open(args.configuration) as confstream:
                configuration = json.load(confstream)

    for k, v in vars(args).items():
        if v:
            configuration[k] = v

    if getpass.getuser() != 'root':
        print("This program must be run as root")
        sys.exit(1)

    home_directory = "/home/" + configuration['user']

    sh("raspi-config nonint do_change_hostname " + configuration['host'])

    for package in configuration['apt_packages']:
        sh("apt-get install %s" % package)
    for package in configuration['pip_packages']:
        sh("pip3 install %s" % package)

    # Add the user (if not already present), with their password
    # disabled but ssh login allowed:
    try:
        _ = pwd.getpwnam(configuration['user'])
    except KeyError:
        sh('adduser --disabled-password --gecos "%s" %s' % (configuration['name'], configuration['user']))
    print("run passwd to set your password")
    print("then on desktop, do this: ssh-copy-id -i ~/.ssh/mykey %s@%s" % (configuration['user'], configuration['host']))

    sh("ssh-keygen -A && update-rc.d ssh enable && invoke-rc.d ssh start") # from the insides of raspi-config

    append_if_missing("/etc/sudoers", configuration['user'], "%s    ALL=(ALL:ALL) ALL\n" % configuration['user'])

    # If there is an external disk attached, put it where I want it:
    drive = "/dev/sda1"
    mountpoint = "/mnt/hdd0"

    if os.path.exists(drive):
        sh("umount " + drive)
        append_if_missing("/etc/fstab", drive, "%s %s ext4 defaults 0 0\n" % (drive, mountpoint))
        os.makedirs(mountpoint, 0o777, True)
        sh("mount " + drive)
        if os.path.isdir(mountpoint):
            for filename in glob.glob(mountpoint+"/*"):
                os.symlink(os.path.join(home_directory, os.path.basename(filename)), filename)

    # Do the rest as the new user
    os.setuid(pwd.getpwnam(configuration['user'])[2])

    projects_dir = os.path.join(home_directory, MY_PROJECTS_DIRECTORY)
    os.makedirs(projects_dir)
    os.chdir(projects_dir)
    for repo in requests.get(MY_GITHUB_LIST).json():
        if not os.path.isdir(os.path.join(projects_dir, repo['name'])):
            sh("git clone " + repo['git_url'])

    # Now copy my dotfiles into place:
    config_dir = os.path.join(projects_dir, MY_CONFIG_PROJECT)
    for dot_file in configuration['dot_files']:
        shutil.copy(os.path.join(config_dir, dot_file),
                         os.path.join(home_directory, "." + dot_file))

if __name__ == "__main__":
    main()
