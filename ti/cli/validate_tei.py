#!/usr/bin/env python

import argparse
import sys
from ti.info.tei import TEI

def main():
    parser = argparse.ArgumentParser(description="Validate TEI input")
    parser.add_argument("--tei-dir", action="store", type=str, help="Directory where input TEI XML files are", required=True)
    parser.add_argument("--schema-dir", action="store", type=str, help="Schema directory", required=True)
    parser.add_argument("--output-dir", action="store", type=str, help="Output directory where the TEI information is stored",required=True)
    parser.add_argument("--config", action="store", type=str, help="Configuration file for validation", required=True)
    parser.add_argument("--quiet", action="store_true", help="Quiet")
    parser.add_argument("--verbose", action="store_true", help="Verbose")
    parser.add_argument("--strict", action="store_true", help="Consider warnings errors")
    args = parser.parse_args()

    if args.quiet:
        verbosity = -1
    elif args.verbose:
        verbosity = 1
    else:
        verbosity = 0

    tei = TEI(args.tei_dir, args.config, verbose=verbosity)
    tei.inventory(args.schema_dir, args.output_dir, carryon=True)

    if not tei.good:
        if tei.severeError or tei.fatalError:
            sys.exit(1)
        elif args.strict:
            #consider warnings errors
            sys.exit(2)
    sys.exit(0)

if __name__ == "__main__":
    main()
