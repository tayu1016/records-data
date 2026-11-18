#!/usr/bin/env python3
"""The release schedule for Syngularail Records, from MusicBrainz's CC0 core data dump.

Reads the tables extracted from mbdump.tar.bz2 (mbdump/<table>) and writes docs/releases-<region>.json: the official
albums, singles and EPs released in a region from two weeks ago to four months ahead, by day.
"""
import datetime as dt, json, os, sys

D = sys.argv[1] if len(sys.argv) > 1 else "mbdump"
OUT = "docs"
REGIONS = {"jp": {"JP", "XW"}, "intl": {"XW", "US", "GB"}}
TYPES = {"1": "Album", "2": "Single", "3": "EP"}
OFFICIAL = "1"

def rows(table):
    with open(os.path.join(D, table), encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line.rstrip("\n").split("\t")

def text(v):
    if v == "\\N": return None
    return v.replace("\\t", "\t").replace("\\n", " ").replace("\\r", "").replace("\\\\", "\\")

today = dt.date.today()
start, end = today - dt.timedelta(days=14), today + dt.timedelta(days=120)

codes = {r[0]: r[1] for r in rows("iso_3166_1")}  # area -> code
wanted_areas = {a for a, c in codes.items() if any(c in s for s in REGIONS.values())}

# release -> [(code, date)]
dates = {}
for r in rows("release_country"):
    if r[1] not in wanted_areas or "\\N" in (r[2], r[3], r[4]): continue
    try: d = dt.date(int(r[2]), int(r[3]), int(r[4]))
    except ValueError: continue
    if start <= d <= end: dates.setdefault(r[0], []).append((codes[r[1]], d))

releases, groups, credits = {}, set(), set()
for r in rows("release"):
    if r[0] in dates and r[5] == OFFICIAL:
        releases[r[0]] = {"gid": r[1], "name": text(r[2]), "ac": r[3], "rg": r[4], "barcode": text(r[9])}
        groups.add(r[4]); credits.add(r[3])

rg = {}
for r in rows("release_group"):
    if r[0] in groups: rg[r[0]] = {"gid": r[1], "type": TYPES.get(r[4])}
ac = {}
for r in rows("artist_credit"):
    if r[0] in credits: ac[r[0]] = text(r[1])

os.makedirs(OUT, exist_ok=True)
for region, want in REGIONS.items():
    out, seen = [], set()
    for rid, rel in releases.items():
        g = rg.get(rel["rg"]) or {}
        if not g.get("type"): continue
        ds = sorted(d for c, d in dates[rid] if c in want)
        if not ds: continue
        key = (g.get("gid"), ds[0])
        if key in seen: continue
        seen.add(key)
        out.append({"id": rel["gid"], "title": rel["name"], "artist": ac.get(rel["ac"], ""), "date": ds[0].isoformat(),
                    "type": g["type"], "group": g.get("gid"), "barcode": rel["barcode"]})
    out.sort(key=lambda x: (x["date"], x["artist"].lower()))
    with open(os.path.join(OUT, f"releases-{region}.json"), "w", encoding="utf-8") as f:
        json.dump({"made": today.isoformat(), "source": "MusicBrainz (CC0)", "releases": out}, f, ensure_ascii=False, separators=(",", ":"))
    print(region, len(out))
