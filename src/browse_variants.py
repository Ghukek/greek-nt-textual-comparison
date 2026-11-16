
#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import json
import sys

BOOKS = [
    "MAT", "MRK", "LUK", "JHN", "ACT", "ROM",
    "1CO", "2CO", "GAL", "EPH", "PHP", "COL",
    "1TH", "2TH", "1TI", "2TI", "TIT", "PHM",
    "HEB", "JAS", "1PE", "2PE", "1JN", "2JN",
    "3JN", "JUD", "REV"
]


def display(value):
    """Print Unicode text safely in Python 2.7."""
    if value is None:
        return u"-"
    if isinstance(value, list):
        if not value:
            return u"(empty)"
        return u" ".join(unicode(item) for item in value)
    return unicode(value)


def get_reference(variant, source):
    """Return the start reference for a source, or None."""
    reference = variant.get(source + "_start_reference")
    if reference is None:
        return None
    return tuple(reference)


def get_anchor(variant):
    """Use source A's reference when available, otherwise source B's."""
    reference = get_reference(variant, "source_a")
    if reference is None:
        reference = get_reference(variant, "source_b")
    return reference


def format_reference(reference):
    if reference is None:
        return u"unknown"
    return u"{}:{}".format(reference[0], reference[1])


def format_source_reference(variant, source):
    start = get_reference(variant, source)
    end = variant.get(source + "_end_reference")

    if start is None:
        return u"-"

    if end is None or tuple(end) == start:
        return format_reference(start)

    return u"{}-{}".format(
        format_reference(start),
        format_reference(tuple(end))
    )


def print_variant(variant):
    source_a = variant["source_a"]
    source_b = variant["source_b"]
    if source_a != "GHT":
        source_a = source_a + " "

    print
    #print u"  ID: {}".format(variant.get("id", u"-"))
    #print u"  Type: {}".format(variant.get("type", u"-"))
    #print u"  Sources: {} vs {}".format(source_a, source_b)

    #print u"  {} reference: {}".format(
    #    source_a, format_source_reference(variant, "source_a"))
    #print u"  {} reference: {}".format(
    #    source_b, format_source_reference(variant, "source_b"))

    print u"  Context before: {}".format(
        display(variant.get("source_a_context_before", [])))

    print u"  {} reading:    {}".format(
        source_a, display(variant.get("source_a_region", [])))
    print u"  {}  reading:    {}".format(
        source_b, display(variant.get("source_b_region", [])))

    print u"  Context after:  {}".format(
        display(variant.get("source_a_context_after", [])))


def choose_book():
    print u"New Testament books:"
    for index, book in enumerate(BOOKS):
        print u"  {:2d}. {}".format(index + 1, book)

    while True:
        answer = raw_input(
            "\nStarting book (number or abbreviation): ").strip().upper()

        if answer.isdigit():
            number = int(answer)
            if 1 <= number <= len(BOOKS):
                return BOOKS[number - 1]

        if answer in BOOKS:
            return answer

        print u"Invalid book. Please try again."


def choose_integer(prompt, minimum=1):
    while True:
        answer = raw_input(prompt).strip()
        try:
            number = int(answer)
            if number >= minimum:
                return number
        except ValueError:
            pass

        print u"Enter a valid integer of at least {}.".format(minimum)


def choose_mode():
    while True:
        print
        print u"Pair selection:"
        print u"  1. GHT pairs only (either source is GHT)"
        print u"  2. All source pairs"

        answer = raw_input("Choose 1 or 2: ").strip()

        if answer in ("1", "2"):
            return answer

        print u"Invalid choice."


def load_variants(filename):
    try:
        with open(filename, "r") as file_handle:
            return json.load(file_handle)
    except IOError:
        print u"Could not open {}.".format(filename)
        sys.exit(1)
    except ValueError as error:
        print u"Invalid JSON: {}".format(error)
        sys.exit(1)


def main():
    variants = load_variants("candidates.json")

    book = choose_book()
    chapter = choose_integer("Starting chapter: ")
    verse = choose_integer("Starting verse: ")
    mode = choose_mode()

    book_index = BOOKS.index(book)
    start_position = (book_index, chapter, verse)

    selected = []

    for variant in variants:
        source_a = variant.get("source_a")
        source_b = variant.get("source_b")

        if mode == "1" and source_a != "GHT" and source_b != "GHT":
            continue

        variant_book = variant.get("book")
        if variant_book not in BOOKS:
            continue

        reference = get_anchor(variant)
        if reference is None:
            continue

        variant_position = (
            BOOKS.index(variant_book),
            reference[0],
            reference[1]
        )

        if variant_position < start_position:
            continue

        selected.append((variant_position, variant))

    selected.sort(key=lambda item: (
        item[0],
        item[1].get("source_a", ""),
        item[1].get("source_b", ""),
        item[1].get("id", "")
    ))

    if not selected:
        print u"\nNo matching variants found from {} {}:{} onward.".format(
            book, chapter, verse)
        return

    # Group all variant units assigned to the same verse.
    grouped = {}

    for position, variant in selected:
        grouped.setdefault(position, []).append(variant)

    print
    print u"Found {} variant units across {} verses.".format(
        len(selected), len(grouped))
    print u"Press Enter to advance one verse; type q to quit."

    for position in sorted(grouped):
        book_name = BOOKS[position[0]]
        chapter_number = position[1]
        verse_number = position[2]
        verse_variants = grouped[position]

        print
        print u"=" * 65
        print u"{} {}:{}  ({} variant units)".format(
            book_name, chapter_number, verse_number,
            len(verse_variants))
        print u"=" * 65

        for variant in verse_variants:
            print_variant(variant)

        answer = raw_input("\nEnter = next verse, q = quit: ").strip().lower()
        if answer == "q":
            break

    print u"\nFinished browsing variants."


if __name__ == "__main__":
    main()

