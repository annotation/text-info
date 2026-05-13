#!/usr/bin/env python

import sys
import argparse
from lxml import etree
from glob import glob
from ti.kit.request import get_base_url, fetch_json

DESCRIPTION = """This script gets image sizes from facsimile mentioned in TEI XML by querying the IIIF server and outputs (to standard output) data for sizes_pages.tsv"""

NSMAP = {
    "tei": "http://www.tei-c.org/ns/1.0",
    "ed": "http://xmlschema.huygens.knaw.nl/ns/editem"
}

def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("--tei-dir", action="store", type=str, help="Directory where input TEI XML files are", required=True)
    parser.add_argument("--iiif-base", action="store", type=str, help="Base URL for IIIF server", required=True)
    parser.add_argument("--ignore-errors", action="store_true", help="Ignore IIIF query errors")
    args = parser.parse_args()

    print("file\twidth\theight")
    for filename in glob(f"{args.tei_dir}/*.xml", recursive=True):
        tree = etree.parse(filename)
        for facs_node in tree.xpath("//tei:facsimile", namespaces=NSMAP):
            for surface_node in facs_node.xpath('./tei:surface', namespaces=NSMAP):
                for graphic_node in surface_node.xpath("./tei:graphic", namespaces=NSMAP):
                    source: str = graphic_node.attrib['url']
                    if source.endswith('default.jpg'):
                        print(f"WARNING: Graphic URL is a full specific URL rather than the excepted IIIF identifier: {source} ... skipping lookup for this one!", file=sys.stderr)
                    elif source == "dummy" or not source:
                        print("WARNING: Skipping dummy or empty source", file=sys.stderr)
                    else:
                        base_url = get_base_url(graphic_node, args.iiif_base)
                        try:
                            if source.startswith(("http://", "https://")):
                                data = fetch_json(f"{source}/info.json")
                            else:
                                data = fetch_json(f"{base_url}/{source}/info.json")
                        except Exception as e:
                            if not args.ignore_errors:
                                raise e
                            else:
                                print(f"WARNING: Skipping {source} due to error: {e}", file=sys.stderr)
                        width = data['width']
                        height = data['height']
                        print(f"{source}\t{width}\t{height}")


if __name__ == "__main__":
    main()
