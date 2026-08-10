import sys
import json
import urllib.request
from typing import Optional
import ssl

ATTRIB_XMLBASE = '{http://www.w3.org/XML/1998/namespace}base'
ATTRIB_XMLID = '{http://www.w3.org/XML/1998/namespace}id'


# fake curl user-agent because RKD server is picky
def fetch_json(url: str, timeout: int = 10, verify_cert=True, user_agent="curl/8.21.0"):
    print(f"(fetching {url})", file=sys.stderr)

    context = ssl.create_default_context()
    if not verify_cert:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, headers={"Accept": "application/ld+json", "User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
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
