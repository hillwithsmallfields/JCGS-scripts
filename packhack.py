#!/usr/bin/env python3

"""Hack packaging files into shape."""

import argparse
import os
import pwd
import re
import sys

import tomlkit

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", "-d", default=".")
    return vars(parser.parse_args())

def get_table(document, name):
    if name in document:
        return document[name]
    document[name] = tomlkit.table()
    return document[name]

def first_name(package):
    return package.split('.')[0] if '.' in package else package

def packhackmain(name, directory="."):
    """Tidy up the packaging files in the current (or given) directory."""
    directory = directory.removesuffix("/")
    if not name:
        name = os.path.basename(os.getcwd() if directory == "." else directory)

    dependencies = set()
    provisions = set()
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(".py") and "site-packages" not in dirpath:
                if os.path.isfile(os.path.join(dirpath, "__init__.py")):
                    import_name = filename.removesuffix(".py")
                    provisions.add(import_name)
                    provisions.add(os.path.basename(dirpath) + "." + import_name)
                fullname = os.path.join(dirpath, filename)
                with open(fullname) as pystream:
                    try:
                        for line in pystream:
                            if (m := re.search("from +([a-z_.0-9]+) +import", line)):
                                dependencies.add(first_name(m.group(1)))
                            elif (m := re.search("import +([a-z_.0-9]+)", line)):
                                dependencies.add(first_name(m.group(1)))
                    except UnicodeDecodeError as e:
                        print("could not scan python file", fullname, oe)

    with open(os.path.join(directory, "requirements.txt"), 'w') as reqstream:
        reqstream.write("\n".join(sorted(set(((dependencies
                                               - sys.stdlib_module_names)
                                              - set(sys.builtin_module_names))
                                             - provisions))))

    tomlfile = os.path.join(directory, "pyproject.toml")
    if os.path.isfile(tomlfile):
        with open(tomlfile) as tom_stream:
            pyproject = tomlkit.parse(tom_stream.read())
    else:
        pyproject = tomlkit.document()

    project = get_table(pyproject, "project")
    for k, v in {
            'authors': [{'name': pwd.getpwuid(os.getuid()).pw_gecos.split(',')[0],
                         'email': os.getenv("EMAIL")}],
            'license': "GPL-3.0-or-later",
            'version': "0.0.1",
            'name': name,
            'readme': "README.md" if os.path.isfile(os.path.join(directory, "README.md")) else "README",
    }.items():
        if k not in project:
            project[k] = v

    build_system = get_table(pyproject, "build-system")
    build_system["requires"] = ["setuptools"]
    build_system["build-backend"] = "setuptools.build_meta"

    with open(tomlfile, 'w') as tom_stream:
        tom_stream.write(tomlkit.dumps(pyproject))

if __name__ == "__main__":
    packhackmain(*get_args())
