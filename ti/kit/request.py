import sys
import json
import urllib.request
from typing import Optional

ATTRIB_XMLBASE = '{http://www.w3.org/XML/1998/namespace}base'
ATTRIB_XMLID = '{http://www.w3.org/XML/1998/namespace}id'


def fetch_json(url: str, timeout: int = 10):
    print(f"(fetching {url})", file=sys.stderr)
    req = urllib.request.Request(url, headers={"Accept": "application/ld+json", "User-Agent": "curl/8.20.0"})  # fake curl user-agent because RKD server is picky
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}")
        data = resp.read()
    return json.loads(data.decode('utf-8'))

def get_base_url(node, default=None) -> Optional[str]:
    if ATTRIB_XMLBASE in node.attrib:
        return node.attrib[ATTRIB_XMLBASE]
    parent = node.getparent()
    if parent:
        return get_base_url(parent,default)
    else:
        return default
