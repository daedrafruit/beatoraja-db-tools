import sqlite3
from pathlib import Path
from collections import defaultdict
import argparse
import shutil
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

def many_folders_by_hash_builder(database):
    """
    Return a mapping of hash → folders,
    but only hashes that are owned by multiple folders
    """
    database.execute("SELECT sha256, path FROM song")

    folders_by_hash = defaultdict(list)

    rows = database.fetchall()
    for row in rows:
        sha256 = row[0]
        file_path = row[1]

        folder_path = str(Path(file_path).parent)

        if folder_path not in folders_by_hash[sha256]:
            folders_by_hash[sha256].append(Path(folder_path))

    many_folders_by_hash = {}

    for sha256 in folders_by_hash:
        folders = folders_by_hash[sha256]

        if len(folders) > 1:
            many_folders_by_hash[sha256] = folders

    return many_folders_by_hash


def merge_folders_to_dest(folders, dest):
    """merge multiple folders into a destination folder using rsync"""
    dest_path = Path(dest)
    bof = Path('/home/daedr/ma-crib/games/bms/charts/BOF2004')
    print(bof)
    for folder in folders:

        path = Path(folder)
        print(path, end='')

        if bof in path.parents: 
            print(' is in bof')
        else: 
            print (' is NOT in bof')

        """
        subprocess.run([
            'rsync', '--ignore-existing', '-a',
            str(path) + '/',
            str(dest_path) + '/'
        ])
        """

def find_merge_folder(folders, folder_priorities):
    for priority in folder_priorities:
        for folder in folders:
            prio_path = Path(priority)
            if priority in folder.parents:
                return folder

    return folders[0]

def run_deduplication(folders_by_hash, folder_priorities):
    for hash in folders_by_hash:
        folders = folders_by_hash[hash]
        if len(folders) < 3: continue
        print(hash)
        merge_path = find_merge_folder(folders_by_hash[hash], folder_priorities)
        for folder in folders:
            print(str(folder))
        print("===")
        for folder in folders:
            if folder == merge_path: continue
            print(str(folder))
        print("->\n" + str(merge_path))
        print()
        print()

def merge_folders(sources, destination):
    for source in sources:
        dest = shutil.move(source, destination)

def main():
    parser = argparse.ArgumentParser(description="Analyze and manage duplicate folders in a beatoraja database.")
    parser.add_argument("--db", required=True, help="Path to song.db")
    parser.add_argument("--samples", type=int, default=0, help="Print out a number of sample hashes to analyze")
    parser.add_argument("--remove", action="store_true", help="Remove redundant entries from the database, not from disk")
    parser.add_argument("--dry-run", action="store_true", help="Simulate folder moves")
    parser.add_argument("--charts-root", help="Root directory of your charts (required for moving)")
    parser.add_argument("--root-priority", nargs='+', help="Priority of folders to merge to, descending")
    args = parser.parse_args()

    abs_root_priorities = []
    for root in args.root_priority:
        abs_root_priorities.append(Path(root).absolute())

    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()


    folder_dict = many_folders_by_hash_builder(cursor)

    run_deduplication(folder_dict, abs_root_priorities)

    conn.close()


if __name__ == "__main__":
    main()
