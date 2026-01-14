import sqlite3
from pathlib import Path
from collections import defaultdict
import argparse
import soundfile as sf
import shutil
import logging
import datetime

logger  = logging.getLogger("")

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

def move_to_trash(src_child, src_root):
    rel = src_child.relative_to(src_root)
    trash_path = Path("./trash" + str(src_root)) / rel.parent
    trash_path.mkdir(parents=True, exist_ok=True)
    shutil.move(src_child, trash_path / src_child.name)


def merge_folder_to_dest(src, dest):
    """Merge folder into destination while preserving non-corrupt audio files."""
    logger.info(f"Merging: {src}")
    logger.info(f"     To: {dest}")

    for src_child in src.iterdir():
        dest_child = dest / src_child.name
        is_audio = src_child.suffix.lower() in {".ogg", ".wav"}

        if not dest_child.exists():
            logger.info("Moving [" + str(src_child.name) + "] (does not exists at dest)")
            shutil.move(src_child, dest)
            continue

        if src_child.is_dir():
            if dest_child.is_dir():
                logger.info("Merging [" + str(src_child.name) + "] (is directory)")
                merge_folder_to_dest(src_child, dest_child)
                continue
            else:
                logger.info("Moving [" + str(src_child.name) + "] (src is directory, dest is file)")
                shutil.move(src_child, dest)
                continue

        if is_audio:
            src_ok = not is_audio_corrupt(src_child)
            dest_ok = not is_audio_corrupt(dest_child)

            if src_ok and not dest_ok:
                logger.info("Trashing [" + str(dest_child.name) + "] (corrupt at dest)")
                move_to_trash(dest_child, src)
                shutil.move(src_child, dest)
                continue

            if dest_ok:
                logger.info("Trashing [" + str(src_child.name) + "] (already exists)")
                move_to_trash(src_child, src)
                continue

        logger.info("Trashing [" + str(src_child.name) + "] (already exists)")

        move_to_trash(src_child, src)


def find_merge_folder(folders, folder_priorities):
    for priority in folder_priorities:
        for folder in folders:
            if folder == priority or priority in folder.parents:
                logger.info(" -> " + str(folder))
                return folder
            else:
                logger.info("    " + str(folder))

    return folders[0]


def run_deduplication(folders_by_hash, folder_priorities, dry_run):
    already_merged = defaultdict(bool)

    for hash in folders_by_hash:
        logger.info("Working: " + hash)
        folders = folders_by_hash[hash]
        merge_path = find_merge_folder(folders_by_hash[hash], folder_priorities)
        worked = True

        for folder in folders:
            if not already_merged[folder] and folder is not merge_path: 
                worked = False
        if worked: 
            continue

        for folder in folders:

            if already_merged[folder]: 
                logger.info("skipping: " + str(folder))
                continue
            if folder == merge_path: continue

            if not dry_run: 
                merge_folder_to_dest(folder, merge_path)
            else:
                logger.info("Merging: " + str(folder))
                logger.info("     to: " + str(merge_path) + "\n")
            already_merged[folder] = True


def main():
    logging.basicConfig(filename="dup_search.log", level=logging.INFO)
    start = datetime.datetime.now()
    logger.info(str(start) + "\nStarting...")

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
    #print(json.dumps(folders_by_hash, indent=4))

    run_deduplication(folders_by_hash, abs_root_priorities, dry_run)

    conn.close()
    end = datetime.datetime.now()
    logger.info(str(end) + "\nCompleted in " + str(end - start))


if __name__ == "__main__":
    main()
