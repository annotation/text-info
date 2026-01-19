#!/usr/bin/env python

import argparse

from ti.info.scans import Scans


def main():
    parser = argparse.ArgumentParser(description="Generate scan information")
    parser.add_argument("sourcedir",
                        help="Path to the scan sources",
                        type=str)
    parser.add_argument("-o", "--reportdir",
                        help="Path to the report directory where output files are written",
                        type=str, default=".")
    parser.add_argument("-c","--config",
                        help="Path to the configuration file",
                        required=True,
                        type=str)
    parser.add_argument("-V","--verbose",
                        help="Verbosity (0 is normal, 1 is verbose)",
                        store="store_true")
    parser.add_argument("-f","--force",
                        help="Whether to run when current results are up to date",
                        action="store_true")
    args = parser.parse_args()

    scans = Scans(args.sourcedir,args.config, 1 if args.verbose else 0, args.force)
    scans.process(args.reportdir, 1 if args.verbose else 0, args.force)


if __name__ == "__main__":
    main()
