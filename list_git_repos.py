#!/usr/bin/env python3
# pylint: disable=unspecified-encoding
"""Output a JSON description of a collection of git repos.

The description is a dictionary in which the keys are the names of
directories in which to run 'git clone', and the values are the
arguments to 'git clone'.

The result can be processed by ./clone_from_list.py.

This pair of programs is meant to install an equivalent set of repos
on a destination machine equivalent to that on the source machine.
"""

import argparse
import configparser
import json
import os
import sys

def get_args():
    """Get the command line args for list_git_repos."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o")
    parser.add_argument("--directory", default=os.path.expandvars("$OPEN_PROJECTS"))
    return vars(parser.parse_args())

def get_clone_url(conf_filename):
    """Get the clonable origin URL from a git config file."""
    try:
        config = configparser.ConfigParser()
        config.read(conf_filename)
        return config['remote "origin"']['url'] if 'remote "origin"' in config else None
    except configparser.MissingSectionHeaderError:
        return None

def git_repos(top_dir):
    """Return a dictionary binding directory names to git URLs.
    The directories are the ones into which to clone those URLs."""
    return {os.path.split(confname
                          .removeprefix(top_dir)
                          .removeprefix("/")
                          .removesuffix("/.git/config"))[0]: clone
            for dirpath, dirnames, filenames in os.walk(top_dir)
            if (os.path.exists(confname := os.path.join(dirpath, "config"))
                and (clone := get_clone_url(confname)))}

def list_git_repos(directory, output):
    """Output a JSON listing of git repos."""
    with open(output) if output else sys.stdout as outstream:
        json.dump(git_repos(directory), outstream, indent=4)

if __name__ == "__main__":
    list_git_repos(**get_args())
