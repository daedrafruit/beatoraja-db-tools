import sqlite3
import json
from pathlib import Path
from collections import defaultdict
import argparse

def find_containing_child(parent_path, child_path):
    parent_path = Path(parent_path).resolve()
    child_path = Path(child_path).resolve()

    try:
        if parent_path not in child_path.parents:
            return None
        return child_path.relative_to(parent_path).parts[0]
    except ValueError:
        return None

def create_table(cursor, charts_dir, flat=False):
    cursor.execute("""
        SELECT
            title,
            genre,
            artist,
            md5,
            sha256,
            path,
            charthash
        FROM song
    """)

    charts_path = Path(charts_dir).resolve()
    table_name = charts_path.name
    folders = defaultdict(list)
    seen_hashes = set()

    for title, genre, artist, md5, sha256, path, charthash in cursor.fetchall():
        if not path or not title or not sha256:
            continue
        if sha256 in seen_hashes:
            continue

        path = Path(path)
        category = find_containing_child(charts_path, path)
        if category is None:
            continue

        seen_hashes.add(sha256)

        song = {
            "class": "bms.player.beatoraja.song.SongData",
            "title": title.strip(),
            "genre": genre.strip() if genre else "",
            "artist": artist.strip() if artist else "",
            "md5": md5,
            "sha256": sha256,
            "content": 3,
            "charthash": charthash
        }

        if flat:
            folders[table_name].append(song)
        else:
            folders[category].append(song)

    return table_name, {
        "name": table_name,
        "folder": [
            {
                "class": "bms.player.beatoraja.TableData$TableFolder",
                "name": folder_name,
                "songs": songs
            }
            for folder_name, songs in sorted(folders.items())
        ]
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create beatoraja table JSON")
    parser.add_argument("--db", required=True, help="Path to song.db")
    parser.add_argument("--charts", nargs='+', required=True, help="Root BMS charts directories")
    parser.add_argument("--output", help="Output JSON file (defaults to <chart_dir_name>.json)")
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Put all songs at the root level (no subfolders)"
    )

    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    for charts_dir in args.charts:
        table_name, table = create_table(cursor, charts_dir, flat=args.flat)

        output_path = (
            Path(args.output) / f"{table_name}.json"
            if args.output
            else Path(f"{table_name}.json")
        )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(table, f, indent=2, ensure_ascii=False)

        print(f"Wrote {output_path}")

    conn.close()

