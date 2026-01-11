import sqlite3
from pathlib import Path
from collections import defaultdict
import argparse
import json
import subprocess
import os


"""
map folders by hash

for each hash, if there are multiple folders
    folder already been moved?
        continue

    merge folders (rsync --ignore-existing)
"""

def build_hashes_by_folder(database):
    """Return a mapping of folder path → list of chart SHA256 hashes."""
    database.execute("SELECT sha256, path FROM song")

    hashes_by_folder = defaultdict(list)

    rows = database.fetchall()
    for row in rows:
        sha256 = row[0]
        file_path = row[1]

        folder_path = str(Path(file_path).parent)

        if folder_path not in hashes_by_folder[sha256]:
            hashes_by_folder[sha256].append(folder_path)

    duplicates = {}

    for sha256 in hashes_by_folder:
        folders = hashes_by_folder[sha256]

        if len(folders) > 1:
            duplicates[sha256] = folders

    return duplicates

def merge_folders_to_dest(folders, dest):
    """merge multiple folders into a destination folder using rsync"""
    dest_path = Path(dest)
    for folder in folders:
        path = Path(folder)

        subprocess.run([
            'rsync', '--ignore-existing', '-a',
            str(path) + '/',
            str(dest_path) + '/'
        ])

def main():
    parser = argparse.ArgumentParser(description="Analyze and manage duplicate folders in a beatoraja database.")
    parser.add_argument("--db", required=True, help="Path to song.db")
    parser.add_argument("--samples", type=int, default=0, help="Print out a number of sample hashes to analyze")
    parser.add_argument("--remove", action="store_true", help="Remove redundant entries from the database, not from disk")
    parser.add_argument("--dry-run", action="store_true", help="Simulate folder moves")
    parser.add_argument("--charts-root", help="Root directory of your charts (required for moving)")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    #folder_dict = build_hashes_by_folder(cursor)
    #print(json.dumps(folder_dict, sort_keys=True, indent=4, ensure_ascii=False))
    merge_folders({'/home/daedr/ma-crib/games/bms/beatoraja/dup_search/test-charts/test-1/', '/home/daedr/ma-crib/games/bms/beatoraja/dup_search/test-charts/test-0/'}, './merge_test')
    merge_folders('', './merge_test')

    conn.close()


if __name__ == "__main__":
    main()
