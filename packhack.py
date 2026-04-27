#!/usr/bin/env python3

"""Hack packaging files into shape."""

import argparse
import os
import pwd
import re
import sys

import git
import tomlkit

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", "-d", default=".")
    parser.add_argument("--output-directory", "--output", "-o")
    parser.add_argument("--verbose", "-v", action='store_true')
    return vars(parser.parse_args())

def get_table(document, name):
    if name in document:
        return document[name]
    document[name] = tomlkit.table()
    return document[name]

def first_name(package):
    return package.split('.')[0] if '.' in package else package

def dependencies_and_provisions(directory):
    """Look for everything we provide that could be imported, and for
    everything we import, in all the python files in the directory
    that aren't in the kind of subdirectories used by virtual
    environments for installed packages."""
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
    return dependencies, provisions

def packhackmain(name, directory=".", verbose=False, output_directory=None):
    """Tidy up the packaging files in the current (or given) directory."""
    directory = directory.removesuffix("/")
    if not output_directory:
        output_directory = directory
    if not name:
        name = os.path.basename(os.getcwd() if directory == "." else directory)

    dependencies, provisions = dependencies_and_provisions(directory)

    if verbose:
        print("Dependencies:")
        for dep in sorted(dependencies):
            print("   ", dep)
        print("Provisions:")
        for prov in sorted(provisions):
            print("   ", prov)

    tomlfile = os.path.join(directory, "pyproject.toml")
    if os.path.isfile(tomlfile):
        with open(tomlfile) as tom_stream:
            pyproject = tomlkit.parse(tom_stream.read())
    else:
        pyproject = tomlkit.document()

    git_reader = git.Repo(".").config_reader()

    project = get_table(pyproject, "project")
    for k, v in {
            'authors': [{'name': git_reader.get("user", "nameb") or pwd.getpwuid(os.getuid()).pw_gecos.split(',')[0],
                         'email': git_reader.get("user", "email") or os.getenv("EMAIL")}],
            'license': "GPL-3.0-or-later",
            'version': "0.0.1",
            'name': name,
            'readme': "README.md" if os.path.isfile(os.path.join(directory, "README.md")) else "README",
    }.items():
        if k not in project:
            print("adding property", k, "with value", v)
            project[k] = v

    version = project['version']
    author_email = project['authors'][0]['email']
    author_name = project['authors'][0]['name']

    setup_name = os.path.join(directory, "setup.py")
    setup = []
    version_found = False
    author_found = False
    email_found = False
    name_found = False
    if os.path.isfile(setup_name):
        with open(setup_name) as setup_stream:
            for line in setup_stream:
                if "name=" in line:
                    name_found = True
                    setup.append('    name="%s"\n' % name)
                elif "version=" in line:
                    version_found = True
                    setup.append('    version="%s"\n' % version)
                elif "author=" in line:
                    author_found = True
                    setup.append('    author="%s"\n' % author_name)
                elif "author_email=" in line:
                    email_found = True
                    setup.append('    author_email="%s"\n' % author_email)
                elif line.startswith(")"):
                    if not name_found:
                        setup.append('    name="%s"\n' % name)
                    if not version_found:
                        setup.append('    version="%s"\n' % version)
                    if not author_found:
                        setup.append('    author="%s"\n' % author_name)
                    if not email_found:
                        setup.append('    author_email="%s"\n' % author_email)
                    setup.append(line)
                else:
                    setup.append(line)

    build_system = get_table(pyproject, "build-system")
    build_system["requires"] = ["setuptools"]
    build_system["build-backend"] = "setuptools.build_meta"

    with open(os.path.join(output_directory, "requirements.txt"), 'w') as reqstream:
        reqstream.write("\n".join(sorted(set(((dependencies
                                               - sys.stdlib_module_names)
                                              - set(sys.builtin_module_names))
                                             - provisions))))
    with open(os.path.join(output_directory, "pyproject.toml"), 'w') as tom_stream:
        tom_stream.write(tomlkit.dumps(pyproject))
    with open(os.path.join(output_directory, "setup.py"), 'w') as setup_stream:
        for line in setup:
            setup_stream.write(line)

if __name__ == "__main__":
    packhackmain(*get_args())
