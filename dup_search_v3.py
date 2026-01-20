import sqlite3
import os
import datetime 
import sys
from pathlib import Path
from collections import defaultdict
import argparse
import shutil

import logging
logger = logging.getLogger(__name__)

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

_folder_empty_cache = {}
def folder_empty(path):
    path = path.resolve()

    cached = _folder_empty_cache.get(path)
    if cached is not None:
        return cached

    with os.scandir(path) as folder:
        for _ in folder:
            _folder_empty_cache[path] = False
            return False

    _folder_empty_cache[path] = True
    return True

def move_to_trash(src):
    if not src.exists():
        return

    src = src.resolve()
    relative_path = src.relative_to(src.anchor)
    trash_dest = Path("./trash") / relative_path

    trash_dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(src, trash_dest)
        return True
    except PermissionError:
        logger.info(f"SKIP (no write permission): {trash_dest.parent}")
        return False


def find_priority_folder(folders, folder_priorities):
    for priority in folder_priorities:
        for folder in folders:
            if not folder.exists():
                continue
            if folder_empty(folder):
                continue
            if folder == priority or priority in folder.parents:
                return folder

    return min(folders, key=lambda p: len(p.parts))


def run_deduplication(folders_by_hash, folder_priorities, canon_folders, dry_run):
    already_removed = set()
    total = len(folders_by_hash)
    for count, sha256 in enumerate(folders_by_hash, start=1):
        logger.info(f"Working: {sha256}")
        print(f"\rWorking ({count}/{total})", end="", flush=True)

        folders = folders_by_hash[sha256]

        priority = find_priority_folder(folders, folder_priorities)
        logger.info(f"Priority: {priority}")

        for folder in folders:
            if not folder.exists():
                continue
            if folder in already_removed:
                continue

            folder_is_canon = any(folder == c or c in folder.parents for c in canon_folders)

            if folder_is_canon:
                continue

            if folder.samefile(priority):
                continue
            if folder in priority.parents:
                continue

            if not dry_run:
                move_to_trash(folder)

            logger.info(f"Trashing: {folder}")
            already_removed.add(folder)


def main():
    Path("logs").mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = f"logs/{timestamp}.log"
    logging.basicConfig(
        filename=log_file,
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.DEBUG,
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    parser = argparse.ArgumentParser(description="Analyze and manage duplicate folders in a beatoraja database.")
    parser.add_argument("--db", required=True, help="Path to song.db")
    parser.add_argument("--root-priority", nargs='+', help="Priority of folders to merge to, descending")
    parser.add_argument("--canon", nargs='+', help="Paths to never delete from")
    parser.add_argument("--dry-run", action="store_true", help="Simulate deduplication, no filesystem writes")
    parser.add_argument("--save-db", action="store_true", help="Save the db, useful for debugging")

    args = parser.parse_args()

    while True:
        user_input = input("Have you rebuilt your beatoraja database? (y/N): ")
        if user_input.lower() == 'y':
            break
        else:
            sys.exit()
        
    start = datetime.datetime.now()
    logger.info("Starting...")

    if args.save_db:
        db_path = Path(args.db)
        Path("saved_dbs").mkdir(exist_ok=True)
        shutil.copyfile(db_path, Path(f"./saved_dbs/{timestamp}"))

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

    run_deduplication(folders_by_hash, root_priorities, canon, args.dry_run)

    conn.close()
    end = datetime.datetime.now()
    logger.info("Completed in " + str(end - start))


if __name__ == "__main__":
    main()
