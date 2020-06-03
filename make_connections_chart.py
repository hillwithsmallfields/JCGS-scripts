#!/usr/bin/env python3

import argparse
import colour
import yaml

def write_connections_chart(data, outfile, grouped, coloured):
    outfile.write("graph connections {\n")
    for groupname, groupmembers in data['groups'].items():
        print(groupname, "includes", groupmembers)
        if grouped:
            outfile.write("    subgraph " + groupname + "_cm {\n")
        for person in groupmembers:
            print("person is", person)
            outfile.write("        " + person + " [label=\"" + person.replace('_', ' ') + "\"")
            if coloured:
                outfile.write(", color=" + str(colour.Color(pick_for=groupname)) + ", style=filled")
            outfile.write("]\n")
        if grouped:
            outfile.write("    }\n")
    for a, bs in data['connections'].items():
        print(a, "knows", bs)
        for b in bs.split():
            outfile.write("    " + a + " -- " + b + "\n")
    outfile.write("}\n")

def main():
    """Show connections between people."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output")
    parser.add_argument("-g", "--grouped", action='store_true')
    parser.add_argument("-c", "--coloured", action='store_true')
    parser.add_argument("inputfile")
    args = parser.parse_args()
    with open(args.inputfile) as infile:
        with open(args.output or (args.inputfile + ".gv"), 'w') as outfile:
            write_connections_chart(yaml.load(infile,
                                              Loader=yaml.SafeLoader),
                                    outfile,
                                    args.grouped,
                                    args.coloured)

if __name__ == "__main__":
    main()
