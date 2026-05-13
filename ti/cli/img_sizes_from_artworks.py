#!/usr/bin/env python

import sys
import argparse
from lxml import etree
from ti.kit.request import ATTRIB_XMLID, get_base_url, fetch_json

DESCRIPTION = """This script gets image sizes from works mentioned in artworks.xml (read from stdin) by querying the IIIF server. It writes data (to standard output) for sizes_illustrations.tsv"""


NSMAP = {
    "tei": "http://www.tei-c.org/ns/1.0",
    "ed": "http://xmlschema.huygens.knaw.nl/ns/editem"
}

def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("--iiif-base", action="store", type=str, help="Base URL for IIIF server", required=True)
    parser.add_argument("--ignore-errors", action="store_true", help="Ignore IIIF query errors")
    args = parser.parse_args()

    data = sys.stdin.read()
    tree = etree.fromstring(data.encode('utf-8'))
    print("file\twidth\theight")
    for artwork_node in tree.xpath("//ed:artwork", namespaces=NSMAP):
        try:
            id: str = artwork_node.attrib[ATTRIB_XMLID]
        except KeyError:
            print("missing xml:id for artwork! skipping...", file=sys.stderr)
            continue
        for graphic_node in artwork_node.xpath("./tei:graphic", namespaces=NSMAP):
            source: str = graphic_node.attrib['url']
            base_url = get_base_url(graphic_node, args.iiif_base)
            try:
                if source.startswith(("http://","https://")):
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
            print(f"{id}\t{width}\t{height}")


if __name__ == "__main__":
    main()
