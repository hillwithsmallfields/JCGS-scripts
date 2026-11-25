#!/usr/bin/env python3
# pylint: disable=unspecified-encoding

"""Program to clone directories from the list produced by ./list_git_repos.py.

This pair of programs is meant to install an equivalent set of repos
on a destination machine equivalent to that on the source machine.
"""

import argparse
import json
import os
import sys

def get_args():
    """Get the command line args for list_git_repos."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--listing", "-l")
    parser.add_argument("--directory", default=os.path.expandvars("$OPEN_PROJECTS"))
    return vars(parser.parse_args())

def clone_from_dict(directory, repos):
    """Clone git repos from a dictionary."""
    original_directory = os.getcwd()
    for subdir, clone_url in repos.items():
        parent = os.path.join(directory, subdir)
        os.makedirs(parent, exist_ok=True)
        os.chdir(parent)
        os.system(f"git clone {clone_url}")
    os.chdir(original_directory)

def clone_git_repos(directory, listing):
    """Apply a JSON listing of git repos."""
    with open(listing) if listing else sys.stdin as instream:
        clone_from_dict(directory, json.load(instream))

if __name__ == "__main__":
    clone_git_repos(**get_args())
