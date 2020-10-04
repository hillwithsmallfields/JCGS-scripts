#!/usr/bin/env python3

import argparse
import yaml
import os.path
import re

def htmlize(string):
    """Convert markup to HTML."""
    m = re.search("(.*)\*(.+)\*(.*)", string)
    return m.group(1) + "<b>" + m.group(2) + "</b>" + m.group(3) if m else string

def output_list(f, contents):
    """Output a YAML list as HTML using nested lists as needed."""
    f.write("        <ul>\n")
    for title, url in contents:
        if isinstance(url, str):
            f.write("          <li> <a href=\"%s\" target=\"_blank\">%s</a></li>\n" % (url, htmlize(title)))
        else:
            f.write("          <li>%s</li>\n" % (title))
            output_list(f, url.items())
    f.write("        </ul>\n")

def safename(name):
    return name.replace(' ', '').replace('-', '').lower()

def output_table(table, filename, stylesheet=None):
    with open(filename, 'w') as f:
        widest = 0
        for groupname, group in table.items():
            groupwidth = len(group)
            if groupwidth > widest:
                widest = groupwidth
        f.write("<html>\n  <head>\n    <title>")
        f.write(os.path.basename(filename).split('.')[0].capitalize())
        f.write("</title>\n")
        if stylesheet:
            f.write("<style>\n")
            with open(stylesheet) as sheet:
                f.write(sheet.read())
            f.write("</style>\n")
        f.write("  </head>\n  <body>\n    <table border>\n")
        for groupname, group in table.items():
            f.write("       <tr><th colspan=\"%d\" class=\"%s\">%s</th></tr>\n"
                    % (widest, safename(groupname), groupname))
            f.write("       <tr class=\"%s\">\n" % safename(groupname))
            for cellname, _ in group.items():
                f.write("         <th class=\"%s\">%s</th>\n"
                        % (safename(cellname), cellname))
            f.write("       </tr>\n")
            f.write("      <tr class=\"%s\">\n" % safename(groupname))
            for cellname, cell in group.items():
                f.write("      <td class=\"%s\">\n" % safename(cellname))
                output_list(f, cell.items())
                f.write("      </td>\n")
            f.write("      </tr>\n")
        f.write("    </table>\n  </body>\n</html>\n")

def main():
    """Make a compact HTML links page."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output")
    parser.add_argument("-s", "--stylesheet")
    parser.add_argument("inputfile")
    args = parser.parse_args()
    with open(args.inputfile) as infile:
        contents = yaml.load(infile, Loader=yaml.SafeLoader)
        output_table(contents,
                     args.output or (args.inputfile + ".html"),
                     stylesheet=args.stylesheet)

if __name__ == "__main__":
    main()
