#!/usr/bin/env python3
"""Check which official WoW API endpoints work for WoW: Forever.

Blizzard documents Retail and Classic but not Forever. This reads the official
endpoint lists from the developer portal (public JSON, no login), rewrites each path
for Forever (realmless characters and guilds, rulesets instead of realms), fills ids
from the index documents, and calls every endpoint in the Forever namespaces.

    python3 forever_api_coverage.py --regions tw --out api-probe.json

Credentials as in forever_api.py (environment or macOS Keychain). A test character
(name-surname, Lv10+) comes from FOREVER_PROBE_CHARACTER; the report and JSON
replace it with {character} and keep only field names, counts and the level.
Prints Markdown (also appended to $GITHUB_STEP_SUMMARY when set).
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forever_api import Api, fetch, get_token  # noqa: E402

PORTAL = "https://community.developer.battle.net/api/pages/content/documentation/{game}/{page}.json"
SOURCES = [("world-of-warcraft", "game-data-apis", "retail"), ("world-of-warcraft", "profile-apis", "retail"),
           ("world-of-warcraft-classic", "game-data-apis", "classic"),
           ("world-of-warcraft-classic", "profile-apis", "classic")]
# Forever-only paths the docs do not list (rulesets replace realms).
FOREVER = [("Ruleset API", "Rulesets Index", "/data/wow/ruleset/index"),
           ("Ruleset API", "Ruleset", "/data/wow/ruleset/{rulesetId}"),
           ("Ruleset API", "Auction House Index", "/data/wow/ruleset/{rulesetId}/auctions/"),
           ("Ruleset API", "Auctions", "/data/wow/ruleset/{rulesetId}/auctions/{auctionHouseId}"),
           ("Ruleset API", "Commodities", "/data/wow/ruleset/{rulesetId}/auctions/{auctionHouseId}/commodities")]
# Classic-era ids tried after the ids found in the indexes and the docs' defaults.
FALLBACK = {"item": [19019, 2840, 2589], "spell": [133, 2050], "creature": [448], "recipe": [2662],
            "creature-display": [1], "item-set": [1], "quest": [1], "title": [1], "achievement": [6]}
PARAM = re.compile(r"\{([^}]+)\}")
TRIES = 3


def kebab(name):
    name = re.sub(r"Id$", "", name)
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def singular(key):
    key = key.lower().replace("_", "-")
    if key.endswith("ies"):
        return key[:-3] + "y"
    if key.endswith(("sses", "xes")):
        return key[:-2]
    if key.endswith("s") and not key.endswith("ss"):
        return key[:-1]
    return key


def load_official():
    """template path -> endpoint info, merged over Retail and Classic."""
    endpoints = {}
    for game, page, source in SOURCES:
        status, _, body = fetch(PORTAL.format(game=game, page=page))
        if status != 200:
            sys.exit(f"official docs {game}/{page}: HTTP {status}")
        for resource in json.loads(body)["resources"]:
            for method in resource["methods"]:
                defaults = {p["name"].strip("{}"): p.get("defaultValue") for p in method.get("parameters", [])}
                kind = str(defaults.get("namespace") or "static").split("-")[0]
                entry = endpoints.setdefault(method["path"], {
                    "api": resource["name"], "name": method["name"], "template": method["path"],
                    "kind": kind, "sources": [], "defaults": {}})
                entry["sources"].append(source)
                for key, value in defaults.items():
                    if key not in ("namespace", "locale") and value not in (None, ""):
                        entry["defaults"].setdefault(key, [])
                        if value not in entry["defaults"][key]:
                            entry["defaults"][key].append(value)
    for api, name, path in FOREVER:
        endpoints[path] = {"api": api, "name": name, "template": path, "kind": "dynamic",
                           "sources": ["forever"], "defaults": {}}
    return endpoints


def forever_path(template):
    """The Forever form of an official path, or None when it needs a user token."""
    if template.startswith("/profile/user/"):
        return None
    path = template.replace("/character/{realmSlug}/{characterName}", "/character/{character}")
    return path.replace("/guild/{realmSlug}/{nameSlug}", "/guild/{guild}")


def id_lists(value, key=None, found=None):
    """Every (key, [ids]) in a document: lists of objects with an id, and single objects with one."""
    found = [] if found is None else found
    if isinstance(value, dict):
        if key and "id" in value and isinstance(value["id"], (int, str)):
            found.append((key, [value["id"]]))
        for k, v in value.items():
            if k != "_links":
                id_lists(v, k, found)
    elif isinstance(value, list):
        ids = [v["id"] for v in value if isinstance(v, dict) and isinstance(v.get("id"), (int, str))]
        if key and ids:
            found.append((key, ids))
        for v in value:
            if isinstance(v, (dict, list)):
                id_lists(v, None, found)
    return found


def longest_list(value):
    best = 0
    if isinstance(value, dict):
        for k, v in value.items():
            if k != "_links":
                best = max(best, longest_list(v))
    elif isinstance(value, list):
        best = max([len(value)] + [longest_list(v) for v in value])
    return best


def has_zh(value):
    text = json.dumps(value, ensure_ascii=False) if value is not None else ""
    return bool(re.search(r"[一-鿿]", text))


def shape(value, depth=0):
    """Field structure without values (for profile documents)."""
    if isinstance(value, dict):
        if depth >= 3:
            return "{…}"
        return {k: shape(v, depth + 1) for k, v in value.items() if k != "_links"}
    if isinstance(value, list):
        return [len(value), shape(value[0], depth + 1)] if value else [0]
    return type(value).__name__


def remember(store, key, ids, cap=20):
    known = store.setdefault(key, [])
    for i in ids:
        if len(known) >= cap:
            break
        if i not in known:
            known.append(i)


class Probe:
    def __init__(self, api, character, guild):
        self.api, self.character, self.guild = api, character, guild
        self.by_path = {}  # concrete path prefix -> ids, e.g. /data/wow/profession/164/skill-tier
        self.by_name = {}  # singular resource name -> ids, e.g. recipe
        self.chosen = {}  # template -> concrete path that answered 200

    def learn(self, result, concrete):
        payload = result.get("payload")
        if result.get("status") != 200 or not isinstance(payload, (dict, list)):
            return
        found = id_lists(payload)
        if concrete.endswith("/index") or concrete.endswith("/auctions/"):
            lists = [ids for _, ids in found if len(ids) > 1] or [ids for _, ids in found]
            if lists:
                base = concrete[:-len("/index")] if concrete.endswith("/index") else concrete.rstrip("/")
                remember(self.by_path, base, max(lists, key=len))
        for key, ids in found:
            remember(self.by_name, singular(key), ids)
            remember(self.by_path, f"{concrete.rstrip('/')}/{singular(key)}", ids)

    def candidates(self, endpoint, path, param, final):
        """Values to try for one path parameter, or None when it should wait for more indexes."""
        if param == "character":
            return [self.character] if self.character else []
        if param == "guild":
            return [g for g in self.guild if g]
        prefix = path.split("{" + param + "}")[0].rstrip("/")
        segment = singular(prefix.rsplit("/", 1)[-1])
        found = []
        for ids in (self.by_path.get(prefix), self.by_name.get(kebab(param)), self.by_name.get(segment)):
            found += [i for i in ids or [] if i not in found]
        if not param.endswith("Id"):
            return (endpoint["defaults"].get(param) or [])[:1]
        if not found and not final:
            return None
        values = found[:1] + endpoint["defaults"].get(param, []) + FALLBACK.get(segment, []) \
            + FALLBACK.get(kebab(param), [])
        return list(dict.fromkeys(values))

    def resolve(self, endpoint, final):
        """Concrete paths to try, None to wait, [] when a value is missing."""
        path = endpoint["forever"]
        # Reuse the id of the longest parent document that answered 200.
        for template, concrete in sorted(self.chosen.items(), key=lambda kv: -len(kv[0])):
            parent = (forever_path(template) or "").rstrip("/")
            if parent and PARAM.search(parent) and path.startswith(parent + "/"):
                path = concrete.rstrip("/") + path[len(parent):]
                break
        params = PARAM.findall(path)
        if not params:
            return [path]
        for param in params[:-1]:  # parents take their first value
            values = self.candidates(endpoint, path, param, final)
            if values is None or not values:
                return values
            path = path.replace("{" + param + "}", str(values[0]))
        last = params[-1]  # the leaf gets up to TRIES values
        values = self.candidates(endpoint, path, last, final)
        if values is None or not values:
            return values
        return list(dict.fromkeys(path.replace("{" + last + "}", str(v)) for v in values[:TRIES]))

    def run(self, endpoint, paths):
        kinds = [endpoint["kind"]] + [k for k in ("static", "dynamic") if k != endpoint["kind"]
                                      and endpoint["kind"] != "profile"]
        tried = []
        params = {"_pageSize": "5"} if "/search/" in endpoint["forever"] else None
        for n, kind in enumerate(kinds):
            for path in paths if n == 0 else paths[:1]:
                result = self.api.get(path, kind, params)
                tried.append({"path": path, "namespace": result["namespace"], "status": result["status"]})
                if result["status"] == 200:
                    return result, tried
        return result, tried

    def report(self, endpoint, result, tried):
        payload = result.get("payload") if result else None
        ok = bool(result) and result["status"] == 200
        row = {"api": endpoint["api"], "name": endpoint["name"], "template": endpoint["template"],
               "forever": endpoint["forever"], "sources": endpoint["sources"],
               "status": result["status"] if result else None,
               "namespace": result["namespace"] if ok else tried[0]["namespace"], "tried": tried}
        if ok:
            row["keys"] = sorted(k for k in payload if k != "_links") if isinstance(payload, dict) else []
            row["longest_list"] = longest_list(payload)
            row["zh_TW"] = has_zh(payload)
            row["last_modified"] = result["last_modified"]
            row["bytes"] = result["bytes"]
            assets = [a.get("value", "") for a in (payload.get("assets") or [])] if isinstance(payload, dict) else []
            if assets:
                row["asset_hosts"] = sorted({urllib.parse.urlsplit(a).netloc for a in assets if a})
                row["asset_sample"] = assets[0] if "{character}" not in endpoint["forever"] else None
            if endpoint["forever"].startswith("/profile/") or "{guild}" in endpoint["forever"]:
                row["shape"] = shape(payload)
                if isinstance(payload, dict) and isinstance(payload.get("level"), int):
                    row["level"] = payload["level"]
            elif isinstance(payload, dict):
                name = payload.get("name")
                row["sample_name"] = name if isinstance(name, str) else None
        return row


def redact(value, secrets):
    text = json.dumps(value, ensure_ascii=False)
    for secret in secrets:
        if secret:
            text = text.replace(secret, "{character}")
    return json.loads(text)


def probe_region(region, token, character, guilds, lines):
    api = Api(region, token)
    endpoints = load_official()
    for endpoint in endpoints.values():
        endpoint["forever"] = forever_path(endpoint["template"])
    probe = Probe(api, character, guilds)
    rows, pending = [], [e for e in endpoints.values() if e["forever"]]
    rows += [{"api": e["api"], "name": e["name"], "template": e["template"], "forever": None,
              "sources": e["sources"], "status": "user-token"} for e in endpoints.values() if not e["forever"]]
    final = False
    with ThreadPoolExecutor(max_workers=6) as pool:
        while pending:
            ready = [(e, probe.resolve(e, final)) for e in pending]
            ready = [(e, paths) for e, paths in ready if paths is not None]
            if not ready:
                if final:
                    break
                final = True
                continue
            done = {id(e) for e, _ in ready}
            pending = [e for e in pending if id(e) not in done]
            jobs = [(e, pool.submit(probe.run, e, paths)) if paths else (e, None) for e, paths in ready]
            for endpoint, job in jobs:
                if job is None:
                    rows.append({"api": endpoint["api"], "name": endpoint["name"], "template": endpoint["template"],
                                 "forever": endpoint["forever"], "sources": endpoint["sources"],
                                 "status": "no-value"})
                    continue
                result, tried = job.result()
                probe.learn(result, tried[-1]["path"])
                if result["status"] == 200:
                    probe.chosen[endpoint["template"]] = tried[-1]["path"]
                rows.append(probe.report(endpoint, result, tried))
            final = False
    static = next((r for r in rows if r.get("namespace", "") and str(r["namespace"]).startswith("static")
                   and r["status"] == 200), None)
    version = None
    if static:
        self_link = api.get(static["tried"][-1]["path"], "static")["payload"]
        href = ((self_link or {}).get("_links") or {}).get("self", {}).get("href", "")
        version = urllib.parse.parse_qs(urllib.parse.urlsplit(href).query).get("namespace", [None])[0]
    secrets = [character, urllib.parse.quote(character or "", safe="-")] if character else []
    rows = redact(sorted(rows, key=lambda r: (r["api"], r["template"])), secrets)
    write_markdown(region, api, version, rows, lines)
    return {"region": region, "static_namespace": version, "calls": api.calls, "character": bool(character),
            "endpoints": rows}


KEY_PATHS = ["/data/wow/profession/index", "/data/wow/profession/{professionId}",
             "/data/wow/profession/{professionId}/skill-tier/{skillTierId}", "/data/wow/recipe/{recipeId}",
             "/data/wow/media/recipe/{recipeId}", "/data/wow/media/profession/{professionId}",
             "/data/wow/item/{itemId}", "/data/wow/media/item/{itemId}", "/data/wow/search/item",
             "/data/wow/spell/{spellId}", "/data/wow/guild/{guild}/roster",
             "/profile/wow/character/{character}/professions"]


def cell(row):
    status = row["status"]
    if status == 200:
        listing = re.search(r"/index$|/search/|/auctions/$", row["forever"] or "")
        note = [f"清單 {row['longest_list']}"] if row.get("longest_list") else ["空清單"] if listing else []
        if row.get("zh_TW"):
            note.append("zh_TW")
        if row.get("asset_hosts"):
            note.append("圖：" + ", ".join(row["asset_hosts"]))
        if row.get("level"):
            note.append(f"Lv{row['level']}")
        if len(row["tried"]) > 1:
            note.append("試過 " + "→".join(str(t["status"]) for t in row["tried"]))
        return "200", "；".join(note)
    if status in ("user-token", "no-value"):
        return status, "需使用者授權碼 token" if status == "user-token" else "缺少參數值（未提供角色？）"
    return str(status), "試過 " + "→".join(f"{t['status']}" for t in row.get("tried", []))


def write_markdown(region, api, version, rows, lines):
    ok = sum(r["status"] == 200 for r in rows)
    lines.append(f"## {region.upper()}：{ok}/{len(rows)} 個端點回 200，static 版本 `{version or '—'}`，"
                 f"共 {api.calls} 次請求\n")
    lines.append("### 專業網站相關\n\n| 端點 | namespace | HTTP | 備註 |\n| --- | --- | --- | --- |")
    by_path = {r["forever"] or r["template"]: r for r in rows}
    for path in KEY_PATHS:
        row = by_path.get(path)
        if row:
            status, note = cell(row)
            lines.append(f"| `{path}` | {(row.get('namespace') or '—').split('-')[0]} | {status} | {note} |")
    lines.append("\n### 全部端點\n")
    current = None
    for row in rows:
        if row["api"] != current:
            current = row["api"]
            lines.append(f"\n#### {current}\n\n| 端點 | 來源 | namespace | HTTP | 備註 |\n| --- | --- | --- | --- | --- |")
        status, note = cell(row)
        lines.append(f"| `{row['forever'] or row['template']}` | {'/'.join(sorted(set(row['sources'])))} | "
                     f"{(row.get('namespace') or '—').split('-')[0]} | {status} | {note} |")
    lines.append("")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--regions", default="tw", help="comma-separated: tw, kr, us, eu")
    parser.add_argument("--guild", default="黎明之劍", help="a public guild name to test realmless guild slugs")
    parser.add_argument("--out", type=Path, help="write the findings as JSON")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    character =(os.environ.get("FOREVER_PROBE_CHARACTER") or "").strip().lower() or None
    if character and os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::add-mask::{character}")
    guild = args.guild.strip().lower()
    guilds = [guild, guild.replace(" ", "-")] if " " in guild else [guild]
    token = get_token()
    lines = [f"# WoW Forever API coverage — {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC\n",
             "Endpoints from the official Retail and Classic docs, called with Forever namespaces. "
             f"Test character: {'set' if character else 'not set (FOREVER_PROBE_CHARACTER)'}; "
             f"guild slug tried: `{guild}`.\n"]
    regions = []
    for region in [r.strip() for r in args.regions.split(",") if r.strip()]:
        regions.append(probe_region(region, token, character, guilds, lines))
    report = "\n".join(lines)
    print(report)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(report + "\n")
    if args.out:
        args.out.write_text(json.dumps({"checkedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                        "guild": guild, "regions": regions}, ensure_ascii=False, indent=1),
                            encoding="utf-8")


if __name__ == "__main__":
    main()
