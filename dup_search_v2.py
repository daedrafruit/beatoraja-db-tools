import sqlite3
from pathlib import Path
from collections import defaultdict
import argparse
import soundfile as sf
import shutil
import datetime

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
        sf.info(audio_file)
    except Exception:
        return True
    return False

def move_to_trash(src):
    if not src.exists():
        return

    src = src.resolve()
    relative_path = src.relative_to(src.anchor)
    trash_dest = Path("./trash") / relative_path

    trash_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(src, trash_dest)


def merge_folder_to_dest(src, dest):
    """Merge folder into destination while preserving non-corrupt audio files."""

    # snapshot children to avoid mutating the directory while iterating
    children = list(src.iterdir())

    for src_child in children:
        dest_child = dest / src_child.name
        is_audio = src_child.suffix.lower() in {".ogg", ".wav"}

        if not dest_child.exists():
            shutil.move(src_child, dest)
            continue

        if src_child.is_dir():
            if dest_child.is_dir():
                merge_folder_to_dest(src_child, dest_child)
                continue
            else:
                move_to_trash(dest_child)
                shutil.move(src_child, dest)
                continue

        if is_audio:
            src_ok = not is_audio_corrupt(src_child)
            dest_ok = not is_audio_corrupt(dest_child)

            if src_ok and not dest_ok:
                move_to_trash(dest_child)
                shutil.move(src_child, dest_child)
                continue

            if dest_ok:
                move_to_trash(src_child)
                continue

        move_to_trash(src_child)


def find_merge_folder(folders, folder_priorities):
    for priority in folder_priorities:
        for folder in folders:
            if not folder.exists():
                continue
            if folder == priority or priority in folder.parents:
                return folder

    return sorted(folders)[0]

def run_deduplication(folders_by_hash, folder_priorities, canon):
    already_merged = set()
    for hash in folders_by_hash:
        print("Working: " + hash)
        folders = folders_by_hash[hash]
        merge_path = find_merge_folder(folders_by_hash[hash], folder_priorities)
        did_merge = False

        for folder in folders:
            if not folder.exists():
                continue
            if folder in already_merged:
                continue

            folder_is_canon = (
                    folder in canon or 
                    bool(len(set(folder.parents).intersection(canon)))
                )

            if folder_is_canon:
                continue

            if folder == merge_path:
                continue
            if merge_path in folder.parents:
                continue
            if folder in merge_path.parents:
                continue

            merge_folder_to_dest(folder, merge_path)
            print("Merged: " + str(folder))
            did_merge = True
            already_merged.add(folder)

        if did_merge: print("Target: " + str(merge_path))


def main():
    start = datetime.datetime.now()
    print(str(start) + "\nStarting...")

    parser = argparse.ArgumentParser(description="Analyze and manage duplicate folders in a beatoraja database.")
    parser.add_argument("--db", required=True, help="Path to song.db")
    parser.add_argument("--root-priority", nargs='+', help="Priority of folders to merge to, descending")
    parser.add_argument("--canon", nargs='+', help="Paths to never delete from")
    args = parser.parse_args()

    root_priorities = []
    if args.root_priority:
        for root in args.root_priority:
            root_priorities.append(Path(root).absolute())

    canon = []
    if args.canon:
        for root in args.canon:
            canon.append(Path(root).absolute())

    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    folders_by_hash = many_folders_by_hash_builder(cursor)

    run_deduplication(folders_by_hash, root_priorities, canon)

    conn.close()
    end = datetime.datetime.now()
    print(str(end) + "\nCompleted in " + str(end - start))


if __name__ == "__main__":
    main()
