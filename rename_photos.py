#!/usr/bin/env python3

import exif
import glob
import os
import re

def metadata_timestamp(filename):
    try:
        timestamp = exif.Image(filename).get('datetime_original')
        if timestamp and (m := re.match("([0-9]{4}):([0-9]{2}):([0-9]{2}) ([0-9:]{8})", timestamp)):
            return "%s-%s-%sT%s" % (m.group(1), m.group(2), m.group(3), m.group(4))
    except:
        return None

def photo_date_name(filename):
    if (m := re.match("([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})(.*)", filename)):
        if m.group(2):
            return m.group(1), m.group(2), True
        else:
            return m.group(1), None, False
    if (m := re.match("((IMG|PXL)_)?([0-9]{8})_([0-9]{6})[0-9]*(.*)\\.jpg", filename)):
        date = m.group(3)
        time = m.group(4)
        return (("%s-%s-%sT%s:%s:%s"
                 % (date[0:4], date[4:6], date[6:8],
                    time[0:2], time[2:4], time[4:6])),
                 m.group(5), False)
    if (m := re.match("([0-9]{4}-[0-9]{2}-[0-9]{2}).([0-9]{2}).([0-9]{2}).([0-9]{2})(.*)\\.jpg", filename)):
        return (("%sT%s:%s:%s"
                 % (m.group(1), m.group(2), m.group(3), m.group(4))),
                m.group(5), False)
    if re.match("dsc[0-9]+\\.jpg", filename):
        return metadata_timestamp(filename), None, False
    return metadata_timestamp(filename), filename.removesuffix(".jpg"), False

def rename_photo(original):
    date, name, done = photo_date_name(original)
    os.system("eog %s" % original)
    print("original is", original, "and date is", date, "and name is", name, "and done is", done)
    response = input("new name: ")

def rename_photos():
    for photo in sorted(glob.glob("*.jpg")):
        rename_photo(photo)

if __name__ == "__main__":
    rename_photos()
