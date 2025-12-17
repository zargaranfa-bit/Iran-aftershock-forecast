#!/usr/bin/env python3
"""
download_usgs.py

Download earthquake events from USGS FDSN for a given bounding box and year range,
and save to a single CSV file.

Usage:
    python download_usgs.py --start-year 1985 --end-year 2024 --out usgs_40yr.csv
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
import time
import requests

DEFAULT_MINLAT = 24.0
DEFAULT_MAXLAT = 42.0
DEFAULT_MINLON = 44.0
DEFAULT_MAXLON = 64.0

def fetch_year(year, minlat, maxlat, minlon, maxlon, timeout=30):
    t0 = f"{year}-01-01"
    t1 = f"{year}-12-31"
    url = (
        "https://earthquake.usgs.gov/fdsnws/event/1/query?"
        f"format=geojson&starttime={t0}&endtime={t1}"
        f"&minlatitude={minlat}&maxlatitude={maxlat}"
        f"&minlongitude={minlon}&maxlongitude={maxlon}"
        "&orderby=time-asc&limit=20000"
    )
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json().get("features", [])

def parse_feature(f):
    p = f.get("properties", {})
    g = f.get("geometry") or {}
    coords = g.get("coordinates") or []
    lon = coords[0] if len(coords) > 0 else None
    lat = coords[1] if len(coords) > 1 else None
    depth = coords[2] if len(coords) > 2 else None
    t_ms = p.get("time")
    time_dt = datetime.utcfromtimestamp(t_ms/1000.0) if t_ms is not None else None
    return {
        "id": f.get("id"),
        "time": time_dt.isoformat() if time_dt is not None else None,
        "mag": p.get("mag"),
        "depth": depth,
        "lon": lon,
        "lat": lat,
        "place": p.get("place"),
        "type": p.get("type")
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=1985)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--minlat", type=float, default=DEFAULT_MINLAT)
    parser.add_argument("--maxlat", type=float, default=DEFAULT_MAXLAT)
    parser.add_argument("--minlon", type=float, default=DEFAULT_MINLON)
    parser.add_argument("--maxlon", type=float, default=DEFAULT_MAXLON)
    parser.add_argument("--out", type=str, default="usgs_40yr.csv")
    parser.add_argument("--resume", action="store_true", help="if out exists, skip download")
    parser.add_argument("--sleep-sec", type=float, default=1.0, help="delay between year requests")
    args = parser.parse_args()

    if args.resume and os.path.exists(args.out):
        print(f"[INFO] {args.out} exists and --resume set -> skipping download.")
        return

    header = ["id", "time", "mag", "depth", "lon", "lat", "place", "type"]

    all_rows = []
    for year in range(args.start_year, args.end_year + 1):
        try:
            print(f"[INFO] Fetching year {year} ...", flush=True)
            feats = fetch_year(year, args.minlat, args.maxlat, args.minlon, args.maxlon)
            for f in feats:
                rec = parse_feature(f)
                # only keep records with mag and time and lat/lon
                if rec["mag"] is None or rec["time"] is None or rec["lat"] is None or rec["lon"] is None:
                    continue
                all_rows.append(rec)
            time.sleep(args.sleep_sec)
            print(f"[INFO] Year {year}: fetched {len(feats)} features; total so far {len(all_rows)}")
        except Exception as e:
            print(f"[WARN] failed to fetch year {year}: {e}", file=sys.stderr)

    # write CSV
    print(f"[INFO] Writing {len(all_rows)} records to {args.out}")
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=header)
        writer.writeheader()
        for r in all_rows:
            writer.writerow(r)
    print("[INFO] Done.")

if __name__ == "__main__":
    main()
