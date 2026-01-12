import sqlite3
from pathlib import Path
from collections import defaultdict
import argparse
import wave
import soundfile as sf
import shutil
import json
import subprocess
import os


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


def find_merge_folder(folders, folder_priorities):
    for priority in folder_priorities:
        for folder in folders:
            prio_path = Path(priority)
            if priority in folder.parents:
                return folder

    return folders[0]


def is_audio_corrupt(audio_file):
    try:
        sf.read(audio_file)
    except:
        return True
    return False


def merge_folder_to_dest(src, dest):
    """
    for each child in src
        exists in dest?
            is a dir?
                recur(child, dest/child)
            is an audio file?
               dest version fail to decode, src version decodes?
                    remove dest version
                    move src version to dest
            remove
        move to dest (recursively for dirs)
    """
    if Path("./tmp").exists:
        Path("./tmp").rmdir
    """merge folder into a destination folder using rsync"""
    print("Merging: " + str(src))
    #dest = Path("./tmp" + str(dest))
    print("     To: " + str(dest))
    #dest.mkdir(exist_ok=True, parents=True)

    for child in src.iterdir():
        dest_child = dest/child.name
        if dest_child.exists(): 
            if child.is_dir():
                merge_folder_to_dest(child, dest_child)
            if any(x == ".ogg" or x == ".wav" for x in child.suffixes):
                print(child, end='')
                if is_audio_corrupt(child):
                    print(" is corrupt")
                else:
                    print(" is NOT corrupt")

    """
    subprocess.run([
        'rsync', '--ignore-existing', '-a',
        str(src) + '/',
        str(test_dir) + '/'
    ])
    """

def run_deduplication(folders_by_hash, folder_priorities):
    """
    for each hash (dict already ensures hash has dupes)
        for each folder

            find highest priority folder

            folder already been moved?
                continue

            merge folders (rsync --ignore-existing)
    """

    already_merged = defaultdict(bool)

    for hash in folders_by_hash:

        folders = folders_by_hash[hash]
        merge_path = find_merge_folder(folders_by_hash[hash], folder_priorities)
        worked = True
        if len(folders) < 3: continue

        for folder in folders:
            if not already_merged[folder] and folder is not merge_path: 
                worked = False
            elif folder is not merge_path:
                print("Already merged (" + hash[:3] + "): " + str(folder))
        if worked: continue


        print("===========================")
        print("\n" + hash)
        for folder in folders:
            print(str(folder))
        print("===")

        
        for folder in folders:

            if already_merged[folder]: continue
            if folder == merge_path: continue

            """
            if merge_folder_to_dest(
                    "/home/daedr/ma-crib/games/bms/charts/Assorted Packs/EventPackage/event/Hyper Remix 2/airen_druggy_HQ",
                    "/home/daedr/ma-crib/games/bms/charts/Assorted Packs/Insane BMS (2025-01-18)/[-45 Remixed by t+pazolite] 藍煉の人形 -druggy's remix-"
                    ):
                already_merged[folder] = True
            """


        print("->\n" + str(merge_path) + "\n")


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

    #run_deduplication(folder_dict, abs_root_priorities)
    merge_folder_to_dest(
                    Path("/home/daedr/ma-crib/games/bms/Illegal BMS/beatmania IIDX 15 DJ TROOPERS/15214 symptom/"),
                    Path("/home/daedr/ma-crib/games/bms/Illegal BMS/beatmania IIDX 15 DJ TROOPERS/15214 symptom/")
                    )

    conn.close()


if __name__ == "__main__":
    main()
