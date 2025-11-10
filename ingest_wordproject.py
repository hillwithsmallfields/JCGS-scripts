#!/usr/bin/env python3

import csv
import collections
import glob
import re

def clean_line_text(line):
    # TODO: remove HTML comment that appears on the last verse of each chapter
    return line

def ingest_wordproject_main():
    for directory in glob.glob("*_new"):
        print("directory", directory)
        m = re.match("(.+)_new", directory)
        language = m.group(1)
        bible_contents = collections.defaultdict(lambda:collections.defaultdict(dict))
        for filename in glob.glob("%s/*/[123456789]*.htm" % directory):
            parts = re.match(".+_new/(.+)/([0-9]+)\\.htm", filename)
            book_number = int(parts.group(1))
            book_name = None
            chapter_number = int(parts.group(2))
            print("  filename", filename)
            with open(filename) as instream:
                try:
                    for line in instream:
                        if (m := re.match("<h1>(.+)</h1>", line)):
                            book_name = m.group(1).strip()
                            if (b := re.match("(.+) [0-9]+", book_name)):
                                new_name = b.group(1)
                                if book_name and (book_name != new_name):
                                    print("name change in", language, "from", book_name, "to", new_name)
                                book_name = new_name
                            book_key = (book_number, book_name)
                        elif (m := re.search('<span class="verse" id="([0-9]+)">[0-9]+ ?</span>(.+)(<.+)?', line)):
                            bible_contents[book_key][chapter_number][int(m.group(1))] = clean_line_text(m.group(2))
                except UnicodeDecodeError as e:
                    print("Could not decode byte sequence in", filename, e)
            # print("after reading", filename, "bible_contents has", len(bible_contents), "entries")
        print("outputting files for", language, "for which there are", len(bible_contents), "books:", sorted(bible_contents.keys()))
        with open(language + ".csv", 'w') as csv_out, open(language + ".org", 'w') as org_out:
            for book_key in sorted(bible_contents.keys()):
                csv_writer = csv.writer(csv_out)
                book_contents = bible_contents[book_key]
                org_out.write("* %d %s\n" % book_key)
                for chapter_key in sorted(book_contents.keys()):
                    org_out.write("** %d\n" % chapter_key)
                    chapter_contents = book_contents[chapter_key]
                    for verse_key in sorted(chapter_contents.keys()):
                        verse_contents = chapter_contents[verse_key]
                        csv_writer.writerow([book_key[0], book_key[1], chapter_key, verse_key, verse_contents])
                        org_out.write("   % 3d %s\n" % (verse_key, verse_contents))

if __name__ == "__main__":
    ingest_wordproject_main()
