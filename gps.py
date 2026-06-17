
import argparse
import csv
import sys

import reverse_geocoder as rg
try:
    import pycountry
    _HAVE_PYCOUNTRY = True
except ImportError:
    _HAVE_PYCOUNTRY = False


LAT_CANDIDATES = ("lat", "latitude", "y")
LON_CANDIDATES = ("lon", "lng", "long", "longitude", "x")


def country_name_from_code(code):
    if not code:
        return ""
    if _HAVE_PYCOUNTRY:
        country = pycountry.countries.get(alpha_2=code)
        if country:
            return country.name
    return code  

def find_column(fieldnames, candidates, explicit=None):
    if explicit:
        if explicit in fieldnames:
            return explicit
        raise ValueError(
            f"Column {explicit!r} not found. Available columns: {fieldnames}"
        )
    lookup = {name.lower(): name for name in fieldnames}
    for cand in candidates:
        if cand in lookup:
            return lookup[cand]
    raise ValueError(
        f"Could not auto-detect a column among {candidates}. "
        f"Available columns: {fieldnames}. Use --lat-col / --lon-col."
    )

def read_coordinates(path, lat_col=None, lon_col=None):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("Input file appears to be empty.")

        lat_field = find_column(reader.fieldnames, LAT_CANDIDATES, lat_col)
        lon_field = find_column(reader.fieldnames, LON_CANDIDATES, lon_col)

        rows = []
        coords = []
        skipped = 0
        for line_no, row in enumerate(reader, start=2):
            try:
                lat = float(row[lat_field])
                lon = float(row[lon_field])
            except (TypeError, ValueError):
                print(f"Skipping line {line_no}: invalid values {row}", file=sys.stderr)
                skipped += 1
                continue

            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                print(f"Skipping line {line_no}: out of range lat={lat}, lon={lon}", file=sys.stderr)
                skipped += 1
                continue
            rows.append(row)
            coords.append((lat, lon))

        if skipped:
            print(f"Skipped {skipped} row(s) with missing/invalid coordinates.",
                  file=sys.stderr)
        return rows, coords, lat_field, lon_field


def main():
    parser = argparse.ArgumentParser(
        description="Reverse-geocode GPS coordinates to countries (offline)."
    )
    parser.add_argument("input", help="Path to input CSV file.")
    parser.add_argument("-o", "--output", default="countries_output.csv",
                        help="Path to output CSV file (default: countries_output.csv).")
    parser.add_argument("--lat-col", help="Name of the latitude column.")
    parser.add_argument("--lon-col", help="Name of the longitude column.")
    args = parser.parse_args()

    rows, coords, lat_field, lon_field = read_coordinates(
        args.input, args.lat_col, args.lon_col
    )

    if not coords:
        print("No valid coordinates found. Nothing to do.", file=sys.stderr)
        sys.exit(1)

    print(f"Reverse-geocoding {len(coords):,} coordinate(s)...")

    results = rg.search(coords) 

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([lat_field, lon_field, "country_code", "country_name",
                         "nearest_place", "admin1"])
        for (lat, lon), res in zip(coords, results):
            code = res.get("cc", "")
            writer.writerow([
                lat,
                lon,
                code,
                country_name_from_code(code),
                res.get("name", ""),
                res.get("admin1", ""),
            ])

    print(f"Done. Wrote {len(results):,} rows to {args.output}")


if __name__ == "__main__":
    main()