import shutil
import datetime
import sys
import sqlite3
from pathlib import Path
from collections import defaultdict
import argparse

def build_hashes_by_folder(database):
    """Return a mapping of folder path → list of chart SHA256 hashes."""
    database.execute("SELECT sha256, path FROM song")

    hashes_by_folder = defaultdict(list)

    for sha256, file_path in database.fetchall():
        folder_path = str(Path(file_path).parent)
        hashes_by_folder[folder_path].append(sha256)

    return hashes_by_folder


def find_subset_statuses(folder_dict):
    """Determine if folders are subsets of others."""
    folder_sets = {
        folder: set(hashes)
        for folder, hashes in folder_dict.items()
    }

    folder_sizes = {f: len(s) for f, s in folder_sets.items()}
    subset_status_by_folder = {f: False for f in folder_sets}

    hash_to_folders = defaultdict(set)
    for folder, hashes in folder_sets.items():
        for h in hashes:
            hash_to_folders[h].add(folder)

    overlap_counts = defaultdict(lambda: defaultdict(int))

    for folders in hash_to_folders.values():
        folders = list(folders)
        for f1 in folders:
            for f2 in folders:
                if f1 != f2:
                    overlap_counts[f1][f2] += 1

    for f1, overlaps in overlap_counts.items():
        size1 = folder_sizes[f1]
        if size1 == 0:
            continue
        for f2, shared in overlaps.items():
            if shared == size1:
                if folder_sizes[f2] > size1 or (folder_sizes[f2] == size1 and f2 < f1):
                    subset_status_by_folder[f1] = True
                    break

    return subset_status_by_folder


def find_maximal_folders(subset_status_by_folder):
    """Return folder names that are not subsets of any other folder."""
    return [Path(f).name for f, subset in subset_status_by_folder.items() if not subset]


def print_samples(cursor, subset_status_by_folder, num_samples):
    """Print sample hashes with their folder subset statuses."""
    cursor.execute("SELECT DISTINCT sha256 FROM song ORDER BY RANDOM() LIMIT ?", (num_samples,))
    sampled_hashes = cursor.fetchall()
    
    print("\nSample Analysis:")
    for i, (sha256,) in enumerate(sampled_hashes, 1):
        cursor.execute("SELECT path FROM song WHERE sha256 = ?", (sha256,))
        paths = [row[0] for row in cursor.fetchall()]
        print(f"\nSample {i}:")
        print(f"Hash: {sha256}")
        print("Paths:")
        for path in paths:
            parent = str(Path(path).parent)
            status = "Max" if not subset_status_by_folder.get(parent, False) else "Sub"
            print(f"{status:>5} -> {parent}")


def remove_subset_entries(cursor, subset_status_by_folder, dry_run=True):
    """Remove all entries in subset folders from the database, with output."""

    subset_folders = []
    for folder, is_subset in subset_status_by_folder.items():
        if is_subset:
            subset_folders.append(folder)

    if not subset_folders:
        return 0

    cursor.connection.create_function(
        "get_parent", 1, lambda p: str(Path(p).parent)
    )

    cursor.execute("""
        SELECT sha256, path
        FROM song
        WHERE get_parent(path) IN (%s)
    """ % ",".join("?" * len(subset_folders)), subset_folders)

    rows = cursor.fetchall()

    for sha256, path in rows:
        parent = str(Path(path).parent)

        cursor.execute(
            "SELECT path FROM song WHERE sha256=? AND path!=?",
            (sha256, path),
        )
        others = [str(Path(p[0]).parent) for p in cursor.fetchall()]

        print(f"DELETE {sha256}")
        print(f"  from: {parent}")
        if others:
            print("  also in:")
            for o in others:
                print(f"    {o}")
        else:
            print("  no other copies found")

    if dry_run:
        print(f"\nWould delete {len(rows)} rows.")
        return len(rows)

    cursor.execute("CREATE TEMP TABLE subset_folders (folder TEXT PRIMARY KEY)")
    cursor.executemany(
        "INSERT INTO subset_folders VALUES (?)",
        [(f,) for f in subset_folders],
    )

    cursor.execute("""
        DELETE FROM song
        WHERE get_parent(path) IN (SELECT folder FROM subset_folders)
    """)

    removed_count = cursor.rowcount
    cursor.execute("DROP TABLE subset_folders")

    print(f"\nDeleted {removed_count} rows.")
    return removed_count


def move_folders_to_bac(subset_status_by_folder, charts_root, dry_run=True):
    """Move subset folders to backup location (_bac appended to charts root)"""
    moved = []
    charts_root = Path(charts_root).resolve()
    backup_root = charts_root.parent / f"{charts_root.name}_bac"
    
    subset_folders = [folder for folder, is_sub in subset_status_by_folder.items() if is_sub]
    
    for folder in subset_folders:
        src = Path(folder).resolve()
        try:
            rel_path = src.relative_to(charts_root)
            dest = backup_root / rel_path
            
            if dry_run:
                moved.append((src, dest))
                continue
                
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            moved.append((src, dest))
            
        except ValueError:
            print(f"Skipping {src} - not under charts root {charts_root}")
    
    return moved


def main():
    parser = argparse.ArgumentParser(description="Analyze and manage duplicate folders in a beatoraja database.")
    parser.add_argument("--db", required=True, help="Path to song.db")
    parser.add_argument("--samples", type=int, default=0, help="Print out a number of sample hashes to analyze")
    parser.add_argument("--remove", action="store_true", help="Remove redundant entries from the database, not from disk")
    parser.add_argument("--dry-run", action="store_true", help="Simulate folder moves")
    parser.add_argument("--charts-root", help="Root directory of your charts (required for moving)")
    parser.add_argument("--save-db", action="store_true", help="Save the db, useful for debugging")
    args = parser.parse_args()

    while True:
        user_input = input("Have you rebuilt your beatoraja database? (y/N): ")
        if user_input.lower() == 'y':
            break
        else:
            sys.exit()

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if args.save_db:
        db_path = Path(args.db)
        Path("saved_dbs").mkdir(exist_ok=True)
        shutil.copyfile(db_path, Path(f"./saved_dbs/{timestamp}"))

    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    folder_dict = build_hashes_by_folder(cursor)
    subset_status_by_folder = find_subset_statuses(folder_dict)
    max_folders = find_maximal_folders(subset_status_by_folder)

    #print("Maximal folders:")
    #for folder in sorted(max_folders):
    #    print(folder)
    print(f"\nTotal maximal folders: {len(max_folders)}")
    print(f"\nTotal subset folders: {len([folder for folder, is_sub in subset_status_by_folder.items() if is_sub])}")



    if args.remove or args.dry_run:
        removed_count = remove_subset_entries(
            cursor,
            subset_status_by_folder,
            dry_run=args.dry_run
        )

    if args.remove and not args.dry_run:
        conn.commit()

    if args.samples > 0:
        print_samples(cursor, subset_status_by_folder, args.samples)

    if args.dry_run or args.charts_root:
        if not args.charts_root:
            print("Error: --charts-root required when using --dry-run")
            return
            
        moved = move_folders_to_bac(
            subset_status_by_folder,
            charts_root=args.charts_root,
            dry_run=args.dry_run
        )
        
        backup_root = Path(args.charts_root).parent / f"{Path(args.charts_root).name}_bac"
        print(f"\nBackup location: {backup_root}")
        

        """
        print("\nOperations:")
        for src, dest in moved:
            status = "Would move" if args.dry_run else "Moved"
            print(f"{status}: {src} -> {dest}")
        """

    conn.close()


if __name__ == "__main__":
    main()
