"""Read the versioned learning-source data in the DungeonsForever catalogue."""

from functools import lru_cache


PROFESSION_IDS = {
    "alchemy": 171, "blacksmithing": 164, "enchanting": 333,
    "engineering": 202, "leatherworking": 165, "tailoring": 197,
}


def learning_sources(text, read_literal, slugs):
    if 'product="wowf"' not in text or 'meta={schema=1,' not in text:
        raise ValueError("Unsupported Forever recipe learning data")
    strings = list(read_literal(text, r"^local STR\s*=").values())
    pools = {
        code: read_literal(text, rf"^local {name}\s*=").split("\n")
        for code, name in (("r", "SHARED"), ("m", "SHAPES"), ("conditions", "CONDITIONS"))
    }

    @lru_cache(maxsize=None)
    def pooled(code, index):
        return unpack(pools[code][index - 1])

    def unpack(value):
        position = 0

        def read():
            nonlocal position
            code = value[position]
            position += 1
            if "A" <= code <= "Z":
                return ord(code) - 64
            if "0" <= code <= "9":
                return ord(code) - 21
            if code in ("z", "t", "f", "_"):
                return {"z": 0, "t": True, "f": False, "_": None}[code]
            if code in ("n", "s", "r", "m"):
                end = value.index(";", position)
                number = int(value[position:end], 36)
                position = end + 1
                if code == "n":
                    return number
                if code == "s":
                    return strings[number - 1]
                if code == "r":
                    return pooled("r", number)
                constants, fields = pooled("m", number)
                return {**dict(zip(constants[::2], constants[1::2])), **{key: read() for key in fields}}
            if code in ("[", "{"):
                end = "]" if code == "[" else "}"
                entries = []
                while value[position] != end:
                    entries.append(read())
                position += 1
                return entries if code == "[" else dict(zip(entries[::2], entries[1::2]))
            raise ValueError(f"Unsupported learning data tag {code}")

        return read()

    sources, grants = {}, {}
    for slug in slugs:
        spells = {}
        spell_id = 0
        for line in read_literal(text, rf'^RAW\["{slug}"\]\s*=').splitlines():
            delta, raw = line.split(":", 1)
            spell_id += int(delta, 36)
            _, _, rows = unpack(raw)
            offers = []
            for row in rows:
                flags = row[0]
                kind = flags % 4
                if flags // 4 % 4 != 1 or flags < 16 or kind not in (1, 2):
                    continue
                conditions = pooled("conditions", row[1 if kind == 1 else 2])
                if any(condition.get("kind") not in ("skill", "level") for condition in conditions):
                    continue
                if any(condition.get("professionID") not in (None, PROFESSION_IDS[slug])
                       for condition in conditions if condition["kind"] == "skill"):
                    continue
                fee = row[3] if kind == 1 and len(row) > 3 else None
                if kind == 1 and not (type(fee) is int and fee >= 0):
                    continue
                offers.append({
                    "item": row[1] if kind == 2 else 0, "fee": fee if kind == 1 else 0,
                    "skill": max((c.get("value", 0) for c in conditions if c["kind"] == "skill"), default=0),
                    "level": max((c.get("value", 0) for c in conditions if c["kind"] == "level"), default=0),
                })
            if offers:
                spells[spell_id] = offers
        sources[slug] = spells
        raw = read_literal(text, rf'^GRANTS\["{slug}"\]\s*=')
        grants[slug] = dict(tuple(map(int, item.split(":"))) for item in raw.split(";") if item)
    return sources, grants
