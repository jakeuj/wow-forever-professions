import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from collect_guild import apply_exclusions, build_artisans, build_overview, get_excluded_ids, roster_characters
from collect_guild import publish_exclusions, refresh_snapshots

NOW = datetime(2026, 11, 19, 4, tzinfo=timezone.utc)


def character(character_id, level):
    return {
        "id": character_id, "name": "測試", "surname": str(character_id),
        "slug": f"test-{character_id}", "level": level, "playable_class": {"id": 2},
    }


class FakeApi:
    def __init__(self):
        self.profiles = set()

    def get(self, path, kind=None, timeout=None):
        parts = path.split("/")
        payload = {}
        status = 200
        if kind == "static":
            profession_id = int(parts[4])
            if len(parts) == 5:
                payload = {"id": profession_id, "skill_tiers": [{"id": 123}]}
            elif profession_id == 197:
                payload = {"categories": [{"recipes": [{"id": 1, "name": "測試布包"}]}]}
        else:
            character_id = int(parts[4].split("-")[-1])
            self.profiles.add(character_id)
            if character_id == 4:
                status = 404
            elif character_id == 5:
                status = 503
            else:
                payload = {"primaries": [
                    {"profession": {"id": 197}, "tiers": [{"skill_points": 150, "max_skill_points": 225,
                      "known_recipes": [{"id": 1, "name": "Test Bag"}, {"id": 10, "name": "Fallback"}]}]},
                    {"profession": {"id": 393}, "tiers": [{"known_recipes": [{"id": 9, "name": "Skinning"}]}]},
                ]}
        return {"status": status, "payload": payload}


class GuildTests(unittest.TestCase):
    def test_overview_counts_each_roster_character_once(self):
        rows = [character(1, 1), character(2, 10), character(3, 11), character(4, 60)]
        roster = roster_characters({"members": [{"character": row} for row in rows + rows[:1]]})
        guild = {"created_timestamp": 1793883600000}
        classes = {"classes": [{"id": 2, "name": "聖騎士"}]}
        overview = build_overview(guild, roster, classes, "Thu, 19 Nov 2026 03:55:00 GMT", NOW)
        self.assertEqual(overview["characterCount"], 4)
        self.assertEqual(overview["levels"], [2, 1, 0, 0, 0, 1])
        self.assertEqual(overview["classes"], [{"name": "聖騎士", "count": 4}])
        self.assertEqual(overview["rosterUpdatedAt"], "2026-11-19T03:55:00+00:00")
        self.assertEqual(overview["expiresAt"], "2026-11-26T04:00:00+00:00")

    def test_directory_handles_missing_and_failed_profiles_and_localizes_recipes(self):
        api = FakeApi()
        rows = [character(1, 9), character(2, 10), character(3, 14), character(4, 23), character(5, 50)]
        snapshot = build_artisans(api, rows, {3}, NOW)
        self.assertEqual(api.profiles, {2, 4, 5})
        self.assertEqual(snapshot["failedProfiles"], 1)
        self.assertEqual(snapshot["artisans"], [{"characterId": 2, "name": "測試 2", "professions": [
            {"id": 197, "skill": 150, "maxSkill": 225, "recipeIds": [1, 10]},
        ]}])
        self.assertEqual(snapshot["recipes"], {
            "1": {"name": "測試布包", "originalName": "Test Bag"}, "10": {"name": "Fallback"},
        })
        updated = build_artisans(FakeApi(), [row for row in rows if row["id"] != 2], {3}, NOW)
        self.assertEqual(updated["artisans"], [])
        self.assertEqual(updated["recipes"], {})

    def test_removal_prunes_only_unreferenced_recipes_and_preserves_expiry(self):
        snapshot = build_artisans(FakeApi(), [character(2, 10), character(3, 10)], set(), NOW)
        reduced = apply_exclusions(snapshot, {2})
        self.assertEqual([row["characterId"] for row in reduced["artisans"]], [3])
        self.assertEqual(reduced["recipes"], snapshot["recipes"])
        empty = apply_exclusions(reduced, {3})
        self.assertEqual(empty["recipes"], {})
        self.assertEqual(empty["fetchedAt"], snapshot["fetchedAt"])
        self.assertEqual(empty["expiresAt"], snapshot["expiresAt"])

    def test_exclusions_reject_malformed_configuration(self):
        self.assertEqual(get_excluded_ids("[20, 20, 32]"), {20, 32})
        for invalid in ("[true]", '["7"]', '{"id":7}', "[0]"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                get_excluded_ids(invalid)

    def test_manual_removal_updates_existing_snapshot_even_without_blizzard(self):
        snapshot = build_artisans(FakeApi(), [character(2, 10)], set(), NOW)
        publisher = Mock()
        publisher.send.return_value = snapshot
        self.assertEqual(publish_exclusions(publisher, {2}, NOW), 1)
        _, filtered = publisher.send.call_args.args
        self.assertEqual(filtered["artisans"], [])
        self.assertEqual(filtered["expiresAt"], snapshot["expiresAt"])
        almost_expired = NOW + timedelta(days=7, minutes=-1)
        self.assertEqual(publish_exclusions(publisher, {2}, almost_expired), 1)
        publisher.send.assert_called_with("artisans", method="DELETE")

    def test_roster_failure_leaves_existing_snapshots_in_place(self):
        publisher = Mock()
        api = Mock()
        api.get.side_effect = [
            {"status": 200, "payload": {"id": 1}}, {"status": 503, "payload": None},
        ]
        with self.assertRaises(ValueError):
            refresh_snapshots(api, publisher, set(), NOW)
        publisher.send.assert_not_called()
