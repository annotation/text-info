#!/usr/bin/env python

import argparse
import sys

from ti.intro.intro_text_factory import IntroTextFactory


def main():
    parser = argparse.ArgumentParser(description="Merge intro texts")
    parser.add_argument("intro_text_path",
                        help="Path to the intro text files to be merged in the given order",
                        nargs='+',
                        type=str)
    args = parser.parse_args()

    merged_xml, errors = IntroTextFactory(args.intro_text_path)
    if errors:
        sys.exit(1)
    else:
        print(merged_xml)
    sys.exit(0)


if __name__ == "__main__":
    main()
