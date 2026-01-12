import sqlite3
from pathlib import Path
from collections import defaultdict
import argparse
import soundfile as sf
import shutil
import os

def many_folders_by_hash_builder(cursor):
    """
    Return a mapping of hash → folders,
    but only hashes that are owned by multiple folders
    """

    folders_by_hash = defaultdict(list)

    for sha256, file_path in cursor.execute("SELECT sha256, path FROM song"):

        folder_path = str(Path(file_path).parent)

        if folder_path not in folders_by_hash[sha256]:
            folders_by_hash[sha256].append(Path(folder_path))

    many_folders_by_hash = {}

    for sha256 in folders_by_hash:
        folders = folders_by_hash[sha256]

        if len(folders) > 1:
            many_folders_by_hash[sha256] = folders

    return many_folders_by_hash

def is_audio_corrupt(audio_file):
    if not audio_file.exists():
        return True
    try:
        sf.read(audio_file)
    except Exception:
        return True
    return False


def merge_folder_to_dest(src, dest):
    """merge folder into a destination folder while considering integrity of audio files"""
    print("Merging: " + str(src))
    print("     To: " + str(dest))

    for src_child in src.iterdir():

        dest_child = dest/src_child.name
        src_is_audio_file = src_child.suffix.lower() in {".ogg", ".wav"}
        dest_not_corrupt = not is_audio_corrupt(dest_child)
        src_not_corrupt = not is_audio_corrupt(src_child)

        if not dest_child.exists(): 
            shutil.move(src_child, dest)
            continue

        if src_child.is_dir():
            if dest_child.is_dir():
                merge_folder_to_dest(src_child, dest_child)
                continue
            else:
                shutil.move(src_child, dest)
                continue

        if src_is_audio_file:

            if dest_not_corrupt:
                os.remove(src_child)
                continue

            if src_not_corrupt:
                shutil.move(src_child, dest)
                continue

        # at this point it exists in dest, and is corrupt on both ends, or is just some random file
        os.remove(src_child)


def find_merge_folder(folders, folder_priorities):
    for priority in folder_priorities:
        for folder in folders:
            if priority in folder.parents or folder == priority:
                return folder

    return folders[0]

def run_deduplication(folders_by_hash, folder_priorities, dry_run):
    already_merged = defaultdict(bool)

    for hash in folders_by_hash:

        folders = folders_by_hash[hash]
        merge_path = find_merge_folder(folders_by_hash[hash], folder_priorities)
        worked = True

        for folder in folders:
            if not already_merged[folder] and folder is not merge_path: 
                worked = False
        if worked: continue

        for folder in folders:

            if already_merged[folder]: continue
            if folder == merge_path: continue

            if not dry_run: 
                merge_folder_to_dest(folder, merge_path)
            else:
                print("Merging: " + str(folder))
                print("     to: " + str(merge_path) + "\n")
            already_merged[folder] = True


def main():
    parser = argparse.ArgumentParser(description="Analyze and manage duplicate folders in a beatoraja database.")
    parser.add_argument("--db", required=True, help="Path to song.db")
    parser.add_argument("--dry-run", action="store_true", help="Simulate folder moves")
    parser.add_argument("--root-priority", nargs='+', help="Priority of folders to merge to, descending")
    args = parser.parse_args()

    dry_run = args.dry_run

    abs_root_priorities = []
    if args.root_priority:
        for root in args.root_priority:
            abs_root_priorities.append(Path(root).absolute())

    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()


    folders_by_hash = many_folders_by_hash_builder(cursor)

    run_deduplication(folders_by_hash, abs_root_priorities, dry_run)

    conn.close()


if __name__ == "__main__":
    main()
