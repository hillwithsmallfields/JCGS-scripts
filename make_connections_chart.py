#!/usr/bin/env python3

import argparse
import colour
import yaml

def write_connections_chart(data, outfile, grouped, coloured, linkorgs):
    outfile.write("graph connections {\n    rankdir=LR\n")
    for groupname, groupmembers in data['groups'].items():
        if grouped:
            outfile.write("    subgraph cluster_" + groupname + "_cm {\n")
        if linkorgs:
            outfile.write("    " + groupname + " [shape=octagon")
            if coloured:
                groupcolour = str(colour.Color(pick_for=groupname))
                outfile.write(", style=filled, color=\"" + groupcolour + "\"")
            outfile.write("]\n")
        for person in groupmembers:
            outfile.write("        " + person + " [label=\"" + person.replace('_', ' ') + "\"")
            if coloured:
                outfile.write(", color=\"" + groupcolour + "\", style=filled")
            outfile.write("]\n")
            if linkorgs:
                outfile.write("        " + person + " -- " + groupname + " [style=dashed")
                if coloured:
                    outfile.write(", color=\"" + groupcolour + "\"")
                outfile.write("]\n")
        if grouped:
            outfile.write("    }\n")
    for a, bs in data['connections'].items():
        for b in bs.split():
            outfile.write("    " + a + " -- " + b + "\n")
    for extragroupname, extragroupmembers in data.get('otheractivities', []).items():
        for person in extragroupmembers.split():
            outfile.write("        " + person + " -- " + groupname + " [style=dashed")
            if coloured:
                outfile.write(", color=\"" + str(colour.Color(pick_for=groupname)) + "\"")
            outfile.write("]\n")

    outfile.write("}\n")

def main():
    """Show connections between people."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output")
    parser.add_argument("-g", "--grouped", action='store_true')
    parser.add_argument("-c", "--coloured", action='store_true')
    parser.add_argument("-l", "--linkorgs", action='store_true')
    parser.add_argument("inputfile")
    args = parser.parse_args()
    with open(args.inputfile) as infile:
        with open(args.output or (args.inputfile + ".gv"), 'w') as outfile:
            write_connections_chart(yaml.load(infile,
                                              Loader=yaml.SafeLoader),
                                    outfile,
                                    args.grouped,
                                    args.coloured,
                                    args.linkorgs)

if __name__ == "__main__":
    main()
