#!/usr/bin/env python3

import argparse
import yaml

def output_list(f, contents):
    f.write("        <ul>\n")
    for title, url in contents:
        if isinstance(url, str):
            f.write("          <li> <a href=\"%s\" target=\"_blank\">%s</a></li>\n" % (url, title))
        else:
            f.write("          <li>%s</li>\n" % title)
            output_list(f, url.items())
    f.write("        </ul>\n")

def output_table(table, f):
    widest = 0
    for groupname, group in table.items():
        groupwidth = len(group)
        if groupwidth > widest:
            widest = groupwidth
    f.write("<html>\n  <head>\n    <title>")
    f.write("</title>  </head>\n  <body>\n    <table border>\n")
    for groupname, group in table.items():
        f.write("       <tr><th colspan=\"%d\">%s</th></tr>\n" % (widest, groupname))
        f.write("       <tr>\n")
        for cellname, _ in group.items():
            f.write("         <th>%s</th>\n" % cellname)
        f.write("       </tr>\n")
        f.write("      <tr>\n")
        for _, cell in group.items():
            f.write("      <td>\n")
            output_list(f, cell.items())
            f.write("      </td>\n")
        f.write("      </tr>\n")
    f.write("    </table>\n  </body>\n</html>\n")

def main():
    """Make a compact HTML links page."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output")
    parser.add_argument("inputfile")
    args = parser.parse_args()
    with open(args.inputfile) as infile:
        with open(args.output or (args.inputfile + ".html"), 'w') as outfile:
            output_table(yaml.load(infile,
                                   Loader=yaml.SafeLoader),
                         outfile)

if __name__ == "__main__":
    main()
