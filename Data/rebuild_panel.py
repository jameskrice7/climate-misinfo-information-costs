"""Reassemble PAPER_2_PANEL.parquet from the parts in Data/panel_parts/.

The full firm-day panel is 2,177 MB, which exceeds GitHub's 100 MB per-file
limit (and Git LFS's 2 GB per-file limit), so it is stored here as a set of
row-group parts of at most 95 MB each. This script puts it back together.

    python Data/rebuild_panel.py                    # -> Data/PAPER_2_PANEL.parquet
    python Data/rebuild_panel.py --verify           # also check part checksums
    python Data/rebuild_panel.py -o /path/panel.parquet

The parts are ordinary parquet files: the row order of the reassembled panel is
identical to the original and every value is preserved exactly. Only the
compression codec differs (zstd here, Snappy in the original), which changes
the bytes on disk but not the data. Each part was checked against its source
row group with pyarrow's Table.equals when the split was made, and all 19
matched. Analysis code that reads the panel is unaffected.

Requires: pyarrow. Needs ~2.2 GB of free disk for the output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
PARTS_DIR = HERE / "panel_parts"
DEFAULT_OUT = HERE / "PAPER_2_PANEL.parquet"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--verify", action="store_true",
                    help="check each part's SHA-256 against the manifest first")
    args = ap.parse_args()

    manifest_path = PARTS_DIR / "manifest.json"
    if not manifest_path.exists():
        sys.exit(f"manifest not found: {manifest_path}")
    man = json.loads(manifest_path.read_text())
    parts = man["parts"]
    print(f"{len(parts)} parts, {man['total_rows']:,} rows expected")

    missing = [p["part"] for p in parts if not (PARTS_DIR / p["part"]).exists()]
    if missing:
        sys.exit(f"missing part files: {', '.join(missing)}")

    if args.verify:
        print("checking part checksums ...")
        bad = [p["part"] for p in parts
               if file_sha256(PARTS_DIR / p["part"]) != p["sha256"]]
        if bad:
            sys.exit(f"CHECKSUM MISMATCH: {', '.join(bad)}")
        print(f"  all {len(parts)} part checksums OK")

    writer = None
    rows = 0
    try:
        for p in parts:
            table = pq.read_table(PARTS_DIR / p["part"])
            if writer is None:
                if table.schema.to_string() != man["arrow_schema"]:
                    sys.exit("SCHEMA MISMATCH: parts do not match the recorded schema")
                writer = pq.ParquetWriter(args.output, table.schema,
                                          compression="zstd", compression_level=9)
            if table.num_rows != p["rows"]:
                sys.exit(f"ROW COUNT MISMATCH in {p['part']}: "
                         f"{table.num_rows:,} != {p['rows']:,}")
            writer.write_table(table)
            rows += table.num_rows
            print(f"  {p['part']}  {rows:>10,} / {man['total_rows']:,}", flush=True)
            del table
    finally:
        if writer is not None:
            writer.close()

    if rows != man["total_rows"]:
        sys.exit(f"ROW COUNT MISMATCH: got {rows:,}, expected {man['total_rows']:,}")

    size_mb = args.output.stat().st_size / 1024**2
    print(f"\nwrote {args.output} — {rows:,} rows, {size_mb:,.1f} MB")


if __name__ == "__main__":
    main()
