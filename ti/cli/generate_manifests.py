#!/usr/bin/env python

import argparse
import sys
from ti.kit.files import fileCopyExpr
from ti.info.iiif import IIIF

def main():
    parser = argparse.ArgumentParser(description="Generate IIIF manifests from TEI XML input")
    parser.add_argument("--tei-info-dir", action="store", type=str, help="Directory where input TEI Info files are. This can be generated with tei-info", required=True)
    parser.add_argument("--tei-dir", action="store", type=str, help="Directory where input TEI XML files are", required=True)
    parser.add_argument("--scaninfo-dir", action="store", type=str, help="Directory where the files with scan information are", required=True)
    parser.add_argument("--output-dir", action="store", type=str, help="Output directory", default=".",required=True)
    parser.add_argument("--config", action="store", type=str, help="Configuration file for manifest generation", required=True)
    parser.add_argument("--title", action="store", type=str, help="Title for the project", required=True)
    parser.add_argument("--base-uri", action="store", type=str, help="Base URI", required=True)
    parser.add_argument("--iiif-base-uri", action="store", type=str, help="IIIF Base URI", required=True)
    parser.add_argument("--quiet", action="store_true", help="Quiet")
    parser.add_argument("--verbose", action="store_true", help="Verbose")
    args = parser.parse_args()

    if args.quiet:
        verbosity = -1
    elif args.verbose:
        verbosity = 1
    else:
        verbosity = 0

    iiif = IIIF(args.tei_info_dir, args.scaninfo_dir, args.config, verbose=verbosity)
    iiif.manifests(
        args.output_dir, title=args.title, baseUri=args.base_uri, iiifBaseUri=args.iiif_base_uri
    )

    if iiif.error:
        sys.exit(1)
    else:
        fileCopyExpr(args.tei_dir, args.output_dir)

if __name__ == "__main__":
    main()
