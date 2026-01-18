import sqlite3
from pathlib import Path
from collections import defaultdict
import argparse
import shutil

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


def move_to_trash(src):
    if not src.exists():
        return
    relative_path = src.relative_to("/")

    trash_dest = Path("./trash") / relative_path
    trash_dest.parent.mkdir(parents=True, exist_ok=True)

    shutil.move(str(src), str(trash_dest))


def find_priority_folder(folders, folder_priorities):
    """
    the "priority" folder is the folder in a set that is:
    - not-empty
    - highest priority
    - if two share priority level, the largest (file count) wins
    """
    best_folder = folders[0]
    best_prio_index = float("inf")
    best_size = -1

    for folder in folders:
        if not folder.exists():
            continue

        size = sum(1 for p in folder.rglob("*") if p.is_file())

        if size == 0:
            continue

        prio_index = float("inf")
        for i, priority in enumerate(folder_priorities):
            if not folder.exists():
                continue
            if folder.samefile(priority):
                prio_index = i
                break
            for parent in folder.parents:
                if priority.samefile(parent):
                    prio_index = i
                    break

        has_higher_priority = prio_index < best_prio_index
        is_larger_with_same_priority = prio_index == best_prio_index and size > best_size
        

        if has_higher_priority or is_larger_with_same_priority:
            best_folder = folder
            best_prio_index = prio_index
            best_size = size

    return best_folder


def is_canon(folder: Path, canon_folders):
    for canon in canon_folders:
        if not folder.exists():
            continue
        if folder.samefile(canon):
            return True
        for parent in folder.parents:
            if parent.samefile(canon):
                return True
    return False

def run_deduplication(folders_by_hash, folder_priorities, canon_folders):
    for sha256 in folders_by_hash:

        print("Working: " + sha256)
        folder_sizes = {}
        folders = folders_by_hash[sha256]
        for folder in folders:
            folder_sizes[folder] = sum(1 for p in folder.rglob("*") if p.is_file())
        print(folder_sizes)
            
        priority = find_priority_folder(folders, folder_priorities)
        print(priority)

        for folder in folders:
            if not folder.exists():
                continue
            if folder.samefile(priority):
                continue
            if is_canon(folder, canon_folders):
                continue

            move_to_trash(folder)
            print("Trashing: " + str(folder))


def main():
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

if __name__ == "__main__":
    main()
