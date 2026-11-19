"""Build the two Dawnblade snapshots and send them to the guild publisher."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from blizzard_api import Api, get_token

GUILD_PATH = "/data/wow/guild/黎明之劍"
MANUFACTURING = {
    197: "裁縫", 165: "製皮", 333: "附魔", 164: "鍛造", 202: "工程學", 171: "鍊金術",
}
SNAPSHOT_LIFETIME = timedelta(days=7)
LOOKUP_ERRORS = (URLError, TimeoutError, ValueError, TypeError, KeyError, OverflowError)


class SnapshotError(ValueError):
    """An error whose message is safe to put in the public workflow log."""


def get_data(api, path, kind):
    result = api.get(path, kind=kind, timeout=12)
    if result["status"] != 200 or not isinstance(result["payload"], dict):
        raise SnapshotError(f"Battle.net {kind} lookup failed (HTTP {result['status']})")
    return result


def snapshot_dates(now):
    return {"schema": 1, "fetchedAt": now.isoformat(), "expiresAt": (now + SNAPSHOT_LIFETIME).isoformat()}


def label(value):
    if isinstance(value, dict):
        value = value.get("zh_TW") or value.get("en_US")
    return value.strip() if isinstance(value, str) else ""


def roster_characters(roster):
    rows = roster.get("members")
    if not isinstance(rows, list):
        raise SnapshotError("Invalid guild roster")
    if any(not isinstance(row, dict) or not isinstance(row.get("character"), dict)
           or type(row["character"].get("id")) is not int for row in rows):
        raise SnapshotError("Invalid guild roster character")
    return list({row["character"]["id"]: row["character"] for row in rows}.values())


def build_overview(guild, characters, classes, last_modified, now):
    created = datetime.fromtimestamp(guild["created_timestamp"] / 1000, timezone.utc)
    levels = [0] * 6
    class_counts = Counter()
    class_labels = {row["id"]: label(row.get("name")) for row in classes["classes"]}
    for character in characters:
        level = character["level"]
        if type(level) is not int or not 1 <= level <= 60:
            raise SnapshotError("Unexpected level in the guild roster")
        levels[(level - 1) // 10] += 1
        class_counts[character["playable_class"]["id"]] += 1
    try:
        roster_updated_at = parsedate_to_datetime(last_modified).astimezone(timezone.utc) if last_modified else now
    except (TypeError, ValueError):
        roster_updated_at = now
    return {
        **snapshot_dates(now),
        "createdAt": created.isoformat(), "rosterUpdatedAt": roster_updated_at.isoformat(),
        "characterCount": len(characters), "levels": levels,
        "classes": [
            {"name": class_labels.get(class_id) or f"職業 {class_id}", "count": count}
            for class_id, count in sorted(class_counts.items(), key=lambda row: (-row[1], row[0]))
        ],
    }


def load_catalog(api, pool, with_profession=False):
    def get_profession(profession_id):
        return get_data(api, f"/data/wow/profession/{profession_id}", "static")["payload"]

    def get_tier(entry):
        profession_id, tier_id = entry
        path = f"/data/wow/profession/{profession_id}/skill-tier/{tier_id}"
        return get_data(api, path, "static")["payload"]

    professions = list(pool.map(get_profession, MANUFACTURING))
    tiers = [(entry["id"], tier["id"]) for entry in professions for tier in entry["skill_tiers"]]
    return {
        row["id"]: (profession_id, label(row.get("name"))) if with_profession else label(row.get("name"))
        for (profession_id, _), tier in zip(tiers, pool.map(get_tier, tiers))
        for category in tier.get("categories", [])
        for row in category.get("recipes", [])
        if label(row.get("name"))
    }


def recipe_reference(value):
    if not isinstance(value, dict) or type(value.get("id")) is not int:
        return None
    return {"id": value["id"], "name": label(value.get("name"))}


def recipe_record(recipe_id, profession_id, name, data):
    product = recipe_reference(data.get("horde_crafted_item") or data.get("crafted_item"))
    quantity = data.get("crafted_quantity") or {}
    if not isinstance(quantity, dict):
        quantity = {"value": quantity}
    units = quantity.get("value") or quantity.get("minimum") or (1 if not quantity else None)
    if type(units) not in (int, float) or not 1 <= units <= 1000 or not float(units).is_integer():
        units = None
    reagents = data.get("reagents")
    materials = None
    if isinstance(reagents, list):
        materials = []
        for row in reagents:
            item = recipe_reference(row.get("reagent"))
            count = row.get("quantity")
            if not item or type(count) is not int or count <= 0:
                materials = None
                break
            materials.append({**item, "quantity": count})
    return {
        "id": recipe_id, "profession": profession_id, "name": label(data.get("name")) or name,
        "product": product, "units": int(units) if product and units else None, "materials": materials,
        "effect": label(data.get("description")) if profession_id == 333 and not product else "",
    }


def refresh_recipes(api, publisher, now):
    def detail(entry):
        recipe_id, (profession_id, name) = entry
        result = api.get(f"/data/wow/recipe/{recipe_id}", kind="static", timeout=8)
        data = result["payload"]
        if result["status"] == 404:
            return None
        if result["status"] != 200 or not isinstance(data, dict):
            raise SnapshotError("Recipe catalog lookup failed")
        return recipe_record(recipe_id, profession_id, name, data)

    with ThreadPoolExecutor(max_workers=10) as pool:
        catalog = load_catalog(api, pool, with_profession=True)
        recipes = [row for row in pool.map(detail, sorted(catalog.items())) if row]
    if not recipes:
        raise SnapshotError("Recipe catalog is empty")
    publisher.send("recipes", {**snapshot_dates(now), "recipes": recipes})
    print(f"Recipe catalog published: {len(recipes)} records")


def read_artisan(api, character):
    """Return a character's valid manufacturing skills, or None if unavailable (404)."""
    path = f"/profile/wow/character/{character['slug']}/professions"
    result = api.get(path, kind="profile", timeout=12)
    if result["status"] == 404:
        return None
    if result["status"] != 200 or not isinstance(result["payload"], dict):
        raise ValueError("Character profession lookup failed")
    skills = []
    for entry in result["payload"].get("primaries", []):
        profession_id = entry["profession"]["id"]
        if profession_id not in MANUFACTURING:
            continue
        tiers = entry.get("tiers", [])
        recipes = {row["id"]: label(row.get("name")) for tier in tiers for row in tier.get("known_recipes", [])}
        if recipes:
            skill, max_skill = max((tier["skill_points"], tier["max_skill_points"]) for tier in tiers)
            skills.append({"id": profession_id, "skill": skill, "maxSkill": max_skill, "recipes": recipes})
    if not skills:
        return None
    name = " ".join(part for field in ("name", "surname") if (part := label(character.get(field))))
    if not name:
        raise ValueError("Character has no display name")
    return {"characterId": character["id"], "name": name, "professions": skills,
            "slug": character["slug"], "level": character["level"], "classId": character["playable_class"]["id"]}


def build_artisans(api, characters, excluded_ids, now):
    def lookup(character):
        try:
            return read_artisan(api, character), False
        except LOOKUP_ERRORS:
            return None, True

    eligible = [character for character in characters if character["level"] >= 10 and character["id"] not in excluded_ids]
    artisans, recipes = [], {}
    failures = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        catalog = load_catalog(api, pool) if eligible else {}
        for artisan, failed in pool.map(lookup, eligible):
            failures += failed
            if artisan is None:
                continue
            for skill in artisan["professions"]:
                known = skill.pop("recipes")
                skill["recipeIds"] = sorted(known)
                for recipe_id, original in known.items():
                    name = catalog.get(recipe_id) or original or f"配方 {recipe_id}"
                    recipes.setdefault(str(recipe_id), {"name": name})
                    if original and original != name:
                        recipes[str(recipe_id)]["originalName"] = original
            artisans.append(artisan)
    return {
        **snapshot_dates(now), "failedProfiles": failures, "professions": MANUFACTURING,
        "recipes": recipes, "artisans": sorted(artisans, key=lambda row: (row["name"], row["characterId"])),
    }


def apply_exclusions(snapshot, excluded_ids):
    artisans = [row for row in snapshot["artisans"] if row["characterId"] not in excluded_ids]
    known = {
        str(recipe_id) for artisan in artisans for skill in artisan["professions"] for recipe_id in skill["recipeIds"]
    }
    recipes = {recipe_id: value for recipe_id, value in snapshot["recipes"].items() if recipe_id in known}
    return {**snapshot, "artisans": artisans, "recipes": recipes}


class Publisher:
    def __init__(self, url, token):
        self.url = url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "dawnblade-guild-collector/1.0 (+https://jakeuj.com/wow-forever-professions/)",
        }

    def send(self, key, snapshot=None, method=None):
        data = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")).encode("utf-8") if snapshot is not None else None
        method = method or ("PUT" if data else "GET")
        request = Request(f"{self.url}/{key}.json", data=data, headers=self.headers, method=method)
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response) if method == "GET" else None
        except HTTPError as error:
            if method == "GET" and error.code == 404:
                return None
            raise SnapshotError(f"Guild publisher rejected {key} (HTTP {error.code})") from None


def get_excluded_ids(raw):
    try:
        ids = json.loads(raw or "[]")
        if isinstance(ids, list) and all(type(value) is int and value > 0 for value in ids):
            return set(ids)
    except json.JSONDecodeError:
        pass
    raise SnapshotError("DAWNBLADE_EXCLUDED_CHARACTER_IDS must be a JSON array of positive integer IDs")


def publish_exclusions(publisher, excluded, now):
    previous = publisher.send("artisans")
    if not previous:
        return 0
    filtered = apply_exclusions(previous, excluded)
    removed = len(previous["artisans"]) - len(filtered["artisans"])
    if removed:
        if datetime.fromisoformat(filtered["expiresAt"]) > now + timedelta(minutes=2):
            publisher.send("artisans", filtered)
        else:
            publisher.send("artisans", method="DELETE")
    return removed


def refresh_snapshots(api, publisher, excluded, now):
    guild = get_data(api, GUILD_PATH, "profile")["payload"]
    roster = get_data(api, GUILD_PATH + "/roster", "profile")
    if roster["payload"]["guild"]["id"] != guild["id"]:
        raise SnapshotError("Guild and roster returned different guild IDs")
    characters = roster_characters(roster["payload"])
    classes = get_data(api, "/data/wow/playable-class/index", "static")["payload"]
    overview = build_overview(guild, characters, classes, roster["last_modified"], now)
    publisher.send("overview", overview)
    print(f"Overview published: {overview['characterCount']} characters")

    artisans = build_artisans(api, characters, excluded, now)
    publisher.send("artisans", artisans)
    print(f"Directory published: {len(artisans['artisans'])} artisans, {len(artisans['recipes'])} recipes, "
          f"{artisans['failedProfiles']} profile lookups failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("refresh", "apply-exclusions", "recipes"), default="refresh")
    args = parser.parse_args()
    excluded = get_excluded_ids(os.getenv("DAWNBLADE_EXCLUDED_CHARACTER_IDS"))
    url = os.getenv("DAWNBLADE_PUBLISH_URL")
    token = os.getenv("DAWNBLADE_PUBLISH_TOKEN")
    if not url or not token:
        raise SnapshotError("Set DAWNBLADE_PUBLISH_URL and DAWNBLADE_PUBLISH_TOKEN in GitHub Actions")
    publisher = Publisher(url, token)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    if args.mode != "recipes":
        publisher.send("character-exclusions", sorted(excluded), method="PUT")

    if excluded:
        removed = publish_exclusions(publisher, excluded, now)
        print(f"Artisan exclusions applied: {removed} removed")
    if args.mode == "refresh":
        refresh_snapshots(Api("tw", get_token()), publisher, excluded, now)
    elif args.mode == "recipes":
        refresh_recipes(Api("tw", get_token()), publisher, now)


if __name__ == "__main__":
    try:
        main()
    except SnapshotError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
    except LOOKUP_ERRORS as error:
        # Malformed API responses can contain member names. Keep their values out of public logs.
        print(f"Guild snapshot update failed ({type(error).__name__})", file=sys.stderr)
        sys.exit(1)
