#!/usr/bin/env python3

import argparse
import yaml

def output_table(table, filename):
    with open(filename, 'w') as f:
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
                f.write("      <td>\n        <ul>\n")
                for title, url in cell.items():
                    f.write("          <li> <a href=\"%s\" target=\"_blank\">%s</a></li>\n" % (url, title))
                f.write("        </ul>\n      </td>\n")
            f.write("      </tr>\n")
        f.write("    </table>\n  </body>\n</html>\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output")
    parser.add_argument("inputfile")
    args = parser.parse_args()
    with open(args.inputfile) as infile:
        contents = yaml.load(infile, Loader=yaml.SafeLoader)
        output_table(contents, args.output or (args.inputfile + ".html"))
        
if __name__ == "__main__":
    main()
    
