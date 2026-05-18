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
    parser.add_argument("--dummy", action='store_true')
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

BUILD_DATA = {
    'setuptools': {
        "requires": ["setuptools"],
        "build-backend": "setuptools.build_meta"

    }
}

def packhackmain(project_name,
                 build_system='setuptools',
                 directory=".",
                 verbose=False,
                 dummy=False,
                 output_directory=None):
    """Tidy up the packaging files in the current (or given) directory."""
    directory = directory.removesuffix("/")
    if not output_directory:
        output_directory = directory
    if not project_name:
        project_name = os.path.basename(os.getcwd() if directory == "." else directory)

    dependencies, provisions = dependencies_and_provisions(directory)

    if verbose:
        print("Dependencies:")
        for dep in sorted(dependencies):
            print("   ", dep)
        print("Provisions:")
        for prov in sorted(provisions):
            print("   ", prov)

    # TODO: make sure there are __init__.py files where needed
    # TODO: check src/ and test/ layout?
    # TODO: check the src/<name> against the project name
    # TODO: look at https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/
    # TODO: look at https://packaging.python.org/en/latest/tutorials/packaging-projects/
    # DONE: look at https://realpython.com/pypi-publish-python-package/
    # TODO: go through https://packaging.python.org/en/latest/specifications/

    tomlfile = os.path.join(directory, "pyproject.toml")
    if os.path.isfile(tomlfile):
        with open(tomlfile) as tom_stream:
            pyproject = tomlkit.parse(tom_stream.read())
    else:
        pyproject = tomlkit.document()

    git_reader = git.Repo(".").config_reader()

    project = get_table(pyproject, "project")
    for k, v in {
            'authors': [{'name': git_reader.get("user", "name") or pwd.getpwuid(os.getuid()).pw_gecos.split(',')[0],
                         'email': git_reader.get("user", "email") or os.getenv("EMAIL")}],
            'license': '{file = "LICENSE"}' if os.path.isfile("LICENSE") else "GPL-3.0-or-later",
            'version': "0.0.1",
            'name': project_name,
            'readme': "README.md" if os.path.isfile(os.path.join(directory, "README.md")) else "README",
            'dependencies': sorted(dependencies),
    }.items():
        if k not in project:
            print("adding property", k, "with value", v)
            project[k] = v
    # TODO: deduce project.scripts?
    # TODO: deduce classifiers?

    version = project['version']
    author_email = project['authors'][0]['email']
    author_name = project['authors'][0]['name']

    setup_name = os.path.join(directory, "setup.py")
    setup = [
        "from setuptools import setup, find_packages",
        "",
        "setup(",
    ]
    version_found = False
    author_found = False
    email_found = False
    name_found = False
    if os.path.isfile(setup_name):
        with open(setup_name) as setup_stream:
            for line in setup_stream:
                if (m := re.search('name="(.+)"', line)):
                    name_found = True
                    proj_name_from_setup = m.group(1)
                    if proj_name_from_setup != project_name:
                        print("Warning: project name mismatch: pyproject.toml says", project_name,
                              "but setup.py says", proj_name_from_setup)
                    setup.append('    name="%s"\n' % proj_name_from_setup)
                elif (m := re.search('version="(.+)"', line)):
                    version_found = True
                    version_from_setup = m.group(1)
                    if version_from_setup != project_name:
                        print("Warning: project version mismatch: pyproject.toml says", version,
                              "but setup.py says", version_from_setup)
                    setup.append('    version="%s"\n' % version_from_setup)
                elif "author=" in line:
                    author_found = True
                    setup.append('    author="%s"\n' % author_name)
                elif "author_email=" in line:
                    email_found = True
                    setup.append('    author_email="%s"\n' % author_email)
                elif line.startswith(")"):
                    if not name_found:
                        setup.append('    name="%s"\n' % project_name)
                    if not version_found:
                        setup.append('    version="%s"\n' % version)
                    if not author_found:
                        setup.append('    author="%s"\n' % author_name)
                    if not email_found:
                        setup.append('    author_email="%s"\n' % author_email)
                    setup.append(line)
                else:
                    setup.append(line)
    setup.append(")")

    build_system_table = get_table(pyproject, "build-system")
    if build_system:
        # force it to use the specified build system
        for k, v in BUILD_DATA[build_system].items():
            build_system_table[k] = v

    # TODO: generate distribution archives: https://packaging.python.org/en/latest/tutorials/packaging-projects/#generating-distribution-archives

    with open(os.path.join(output_directory, "requirements.txt"), 'w') as reqstream:
        reqstream.write("\n".join(sorted(set(((dependencies
                                               - sys.stdlib_module_names)
                                              - set(sys.builtin_module_names))
                                             - provisions))))
    with open(os.path.join(output_directory, "pyproject.toml"), 'w') as tom_stream:
        tom_stream.write(tomlkit.dumps(pyproject))
    with open(os.path.join(output_directory, "setup.py"), 'w') as setup_stream:
        setup_stream.write("\n".join(setup))

    if not dummy:
        # TODO: call this directly in python
        os.system(["python3", "-m", "build",
                   # "--sdist",
                   # "--wheel",
                   directory])
        # TODO: work out the package name
        os.system(["python3", "-m", "twine", "upload",
                   "dist/*"
                   # os.path.join("dist", package_name + ".tar.gz"),
                   # os.path.join("dist", package_name + "py3-none-any.whl"),
                   )

if __name__ == "__main__":
    packhackmain(*get_args())
