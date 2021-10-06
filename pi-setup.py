#!/usr/bin/python3

import argparse
import getpass
import glob
import os
import pwd
import requests
import shutil
import sys

APT_PACKAGES=["emacs"]
PIP_PACKAGES=[
    "measurement",
    "ordered_set",
    "oura",
    "overpass2",
    "pycrypto",
    "python-decouple",
    "pyyaml",
    "sexpdata",
    "webpy"
    ]
DOT_FILES=["emacs", "bashrc", "bash_profile"]

MY_PROJECTS_DIRECTORY="%s/open-projects/github.com/hillwithsmallfields"
MY_CONFIG_PROJECT="JCGS-config"
MY_GITHUB_LIST="https://api.github.com/users/hillwithsmallfields/repos"

def in_fstab(drive):
    with open("/etc/fstab") as fstab:
        return any((entry.startswith(drive) for entry in fstab))

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--user")
    parser.add_argument("--name")
    parser.add_argument("--host")
    args = parser.parse_args()

    if getpass.getuser() != 'root':
        print("This program must be run as root")
        sys.exit(1)

    home_directory = "/home/" + args.user

    os.system("raspi-config nonint do_change_hostname " + args.host)

    for package in APT_PACKAGES:
        print("installing", package, "with apt-get")
        os.system("apt-get install %s" % package)
    for package in PIP_PACKAGES:
        print("installing", package, "with pip3")
        os.system("pip3 install %s" % package)

    # Add the user, with their password disabled but ssh login allowed
    try:
        _ = pwd.getpwnam(args.user)
    except KeyError:
        os.system('adduser --disabled-password --gecos "%s" %s gpio' % (args.user, args.name))
    print("on desktop, do this: ssh-copy-id -i ~/.ssh/mykey %s@%s" % (args.user, args.host))

    with open("/etc/sudoers", 'a') as sudoers:
        sudoers.write("%s    ALL=(ALL:ALL) ALL\n" % args.user)

    drive = "/dev/sda1"
    mountpoint = "/mnt/hdd0"
    if os.path.exists(drive):
        if not in_fstab(drive):
            system("umount " + drive)
            if not os.path.exists("/etc/fstab-old"):
                shutil.copy_file("/etc/fstab", "/etc/fstab-old")
            with open("/etc/fstab", 'a') as fstab:
                fstab.write("%s %s ext4 defaults 0 0\n" % (drive, mountpoint))
            os.makedirs(mountpoint, exists_ok=True)
            system("mount " + drive)
        if os.path.isdir(mountpoint):
            for filename in glob.glob(mountpoint+"/*"):
                os.symlink(os.path.join(home_directory, os.path.basename(filename)), filename)

    # Do the rest as the new user
    os.setuid(pwd.getpwnam(args.user)[2])

    projects_dir = os.path.join(home_directory, MY_PROJECTS_DIRECTORY)
    os.chdir(projects_dir)
    for repo in requests.get(MY_GITHUB_LIST).json():
        if not os.path.isdir(os.path.join(projects_dir, repo['name'])):
            print("Cloning", repo['name'])
            os.system("git clone " + repo['git_url'])

    config_dir = os.path.join(MY_PROJECTS_DIRECTORY, MY_CONFIG_PROJECT)
    for dot_file in DOT_FILES:
        shutil.copy_file(os.path.join(config_dir, dot_file),
                         os.path.join(home_directory, "." + dot_file))

if __name__ == "__main__":
    main()
