#!/usr/bin/env python3
"""Query the Battle.net API for WoW: Forever (standard library only).

Credentials come from BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET; when those are
not set (macOS only), from the Keychain item whose service is `wow-forever-battlenet`
(account = client ID, password = client secret):

    security add-generic-password -s wow-forever-battlenet -a '<client id>' -w

On Windows set the two variables for the current PowerShell session instead
(works in Windows PowerShell 5.1 and PowerShell 7; the secret is not echoed):

    $env:BLIZZARD_CLIENT_ID = '<client id>'
    $env:BLIZZARD_CLIENT_SECRET = [Net.NetworkCredential]::new('', (Read-Host 'client secret' -AsSecureString)).Password

The access token stays in memory and in the Authorization header; it is never
printed or written to disk.

    python3 forever_api.py get /data/wow/ruleset/index
    python3 forever_api.py get /data/wow/profession/index --locale all
    python3 forever_api.py get /data/wow/search/item --param name.zh_TW=亞麻布 --param _pageSize=5
    python3 forever_api.py character <name-surname> --part professions

The namespace is picked from the path (`/profile/...` and guilds use profile,
rulesets and auctions use dynamic, everything else static); --ns overrides it.
Character data goes to the terminal only; do not commit it.
"""

import argparse
import base64
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TOKEN_URL = "https://oauth.battle.net/token"
KEYCHAIN_SERVICE = "wow-forever-battlenet"
LOCALES = {"tw": "zh_TW", "kr": "ko_KR", "us": "en_US", "eu": "en_GB"}
USER_AGENT = "wow-forever-skill"
# Resources the official docs publish in a dynamic namespace (plus Forever's rulesets).
DYNAMIC = re.compile(r"^/data/wow/(ruleset|connected-realm|realm|region|token|pvp-season|pvp-region"
                     r"|mythic-keystone|mythic-leaderboard|leaderboard|auctions)(/|$)|/auctions(/|$)")


def fetch(url, headers=None, data=None, timeout=60):
    """Return (status, headers, body); 4xx comes back as a status, other errors retry."""
    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip", **(headers or {})}
    for attempt in range(4):
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return resp.status, resp.headers, body
        except urllib.error.HTTPError as error:
            if 400 <= error.code < 500 and error.code != 429 or attempt == 3:
                return error.code, error.headers, error.read()
        except (urllib.error.URLError, TimeoutError):
            if attempt == 3:
                raise
        time.sleep(2 ** (attempt + 1))
    raise AssertionError("unreachable")


def credentials():
    """(client id, client secret) from the environment, else the macOS Keychain."""
    client_id = os.environ.get("BLIZZARD_CLIENT_ID")
    secret = os.environ.get("BLIZZARD_CLIENT_SECRET")
    if client_id and secret:
        return client_id, secret
    if sys.platform == "darwin" and shutil.which("security"):
        item = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE],
                              capture_output=True, text=True)
        account = re.search(r'"acct"<blob>="([^"]*)"', item.stdout)
        if item.returncode == 0 and account:
            password = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
                                      capture_output=True, text=True)
            if password.returncode == 0 and password.stdout.strip():
                return account.group(1), password.stdout.strip()
    if sys.platform == "darwin":
        hint = ("or add them to the Keychain with: "
                f"security add-generic-password -s {KEYCHAIN_SERVICE} -a '<client id>' -w")
    else:
        hint = ("e.g. in PowerShell: $env:BLIZZARD_CLIENT_SECRET = "
                "[Net.NetworkCredential]::new('', (Read-Host 'client secret' -AsSecureString)).Password")
    sys.exit(f"No Battle.net credentials: set BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET, {hint}")


def get_token():
    client_id, secret = credentials()
    basic = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    status, _, body = fetch(TOKEN_URL, {"Authorization": f"Basic {basic}",
                                        "Content-Type": "application/x-www-form-urlencoded"},
                            data=b"grant_type=client_credentials", timeout=30)
    if status != 200:
        # The error body names the problem (e.g. invalid_client) and holds no secret.
        sys.exit(f"token request failed: HTTP {status} {body[:300].decode('utf-8', 'replace')}")
    token = json.loads(body)["access_token"]
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::add-mask::{token}")
    return token


def namespace_kind(path):
    if path.startswith("/profile/") or path.startswith("/data/wow/guild/"):
        return "profile"
    return "dynamic" if DYNAMIC.search(path) else "static"


def strip_links(value):
    if isinstance(value, dict):
        return {k: strip_links(v) for k, v in value.items() if k != "_links"}
    if isinstance(value, list):
        return [strip_links(v) for v in value]
    return value


class Api:
    """GET helper for one region's Forever namespaces."""

    def __init__(self, region="tw", token=None, locale=None):
        self.region = region
        self.base = f"https://{region}.api.blizzard.com"
        self.locale = LOCALES.get(region, "en_US") if locale is None else locale
        self.auth = {"Authorization": f"Bearer {token or get_token()}"}
        self.calls = 0

    def namespace(self, kind):
        return kind if "-" in kind else f"{kind}-forever-{self.region}"

    def get(self, path, kind=None, params=None):
        """Return {url, status, namespace, payload, bytes, last_modified}; the url holds no token."""
        namespace = self.namespace(kind or namespace_kind(path))
        query = {"namespace": namespace, **({"locale": self.locale} if self.locale else {}), **(params or {})}
        url = f"{self.base}{urllib.parse.quote(path, safe='/-_.~')}?{urllib.parse.urlencode(query)}"
        self.calls += 1
        status, headers, body = fetch(url, self.auth)
        try:
            payload = json.loads(body) if body else None
        except ValueError:
            payload = None
        return {"url": url, "status": status, "namespace": namespace, "payload": payload, "bytes": len(body),
                "last_modified": headers.get("Last-Modified") if headers else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--region", default="tw", choices=sorted(LOCALES))
    parser.add_argument("--ns", help="static, dynamic, profile, or a full namespace such as static-1.60.1_70399-forever-tw")
    parser.add_argument("--locale", help="default: the region's locale; 'all' returns every locale")
    parser.add_argument("--links", action="store_true", help="keep _links in the output")
    sub = parser.add_subparsers(dest="command", required=True)
    get = sub.add_parser("get", help="GET any API path")
    get.add_argument("path", help="e.g. /data/wow/ruleset/index")
    get.add_argument("--param", action="append", default=[], metavar="KEY=VALUE",
                     help="extra query parameter (search fields, _page, _pageSize, orderby)")
    char = sub.add_parser("character", help="character profile (Lv10+, after a logout)")
    char.add_argument("name", help="name-surname, e.g. thrall-doomhammer")
    char.add_argument("--part", help="sub-resource such as professions, equipment, specializations, character-media")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    locale = "" if args.locale == "all" else args.locale
    api = Api(args.region, locale=locale)
    if args.command == "get":
        path = args.path if args.path.startswith("/") else "/" + args.path
        params = dict(p.split("=", 1) for p in args.param)
    else:
        path = f"/profile/wow/character/{args.name.strip().lower()}" + (f"/{args.part}" if args.part else "")
        params = {}
    result = api.get(path, args.ns, params)
    print(f"HTTP {result['status']} {result['namespace']}"
          + (f" Last-Modified: {result['last_modified']}" if result["last_modified"] else ""), file=sys.stderr)
    payload = result["payload"] if args.links else strip_links(result["payload"])
    if payload is not None:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(0 if result["status"] == 200 else 1)


if __name__ == "__main__":
    main()
