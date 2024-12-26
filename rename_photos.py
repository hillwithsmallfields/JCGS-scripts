#!/usr/bin/env python3

import glob

def rename_photos():
    for photo in glob.glob("*.jpg"):
        print photo

if __name__ == "__main__":
    rename_photos()
