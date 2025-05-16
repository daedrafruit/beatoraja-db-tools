import shutil
import sqlite3
from pathlib import Path
from collections import defaultdict
import argparse

def create_folder_to_files_dictionary(database):
    """Map each directory to its file hashes."""
    database.execute("SELECT sha256, path FROM song")
    dictionary = defaultdict(list)
    for sha256, path in database.fetchall():
        parent = str(Path(path).parent)
        dictionary[parent].append(sha256)
    return dictionary

def find_subset_statuses(folder_dict):
    """Determine if folders are subsets of others."""
    folders = list(folder_dict.keys())
    folder_sets = {f: set(hashes) for f, hashes in folder_dict.items()}
    is_subset = {f: False for f in folders}

    for i, folder1 in enumerate(folders):
        set1 = folder_sets[folder1]
        for folder2 in folders[i+1:]:
            set2 = folder_sets[folder2]
            if set1 <= set2:
                is_subset[folder1] = True
                break
            elif set2 <= set1:
                is_subset[folder2] = True

    return is_subset

def find_maximal_folders(is_subset):
    """Return folder names that are not subsets of any other folder."""
    return [Path(f).name for f, subset in is_subset.items() if not subset]

def print_samples(cursor, is_subset, num_samples):
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
            folder_name = Path(parent).name
            status = "Max" if not is_subset.get(parent, False) else "Sub"
            print(f"{status:>5} -> {parent}")

def remove_subset_entries(cursor, is_subset):
    """Remove all entries in subset folders from the database."""
    subset_folders = []
    for folder, is_sub in is_subset.items():
        if is_sub:
            folder_tuple = (folder,)
            subset_folders.append(folder_tuple)

    if not subset_folders:
        return 0

    cursor.execute("CREATE TEMP TABLE subset_folders (folder TEXT PRIMARY KEY)")
    cursor.executemany("INSERT INTO subset_folders VALUES (?)", subset_folders)

    cursor.connection.create_function("get_parent", 1, lambda p: str(Path(p).parent))

    cursor.execute("""
        DELETE FROM song
        WHERE get_parent(path) IN (SELECT folder FROM subset_folders)
    """)
    removed_count = cursor.rowcount

    cursor.execute("DROP TABLE subset_folders")
    return removed_count

def move_folders(is_subset, charts_root, dry_run=True):
    """Move subset folders to backup location (_bac appended to charts root)"""
    moved = []
    charts_root = Path(charts_root).resolve()
    backup_root = charts_root.parent / f"{charts_root.name}_bac"
    
    subset_folders = [folder for folder, is_sub in is_subset.items() if is_sub]
    
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
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    folder_dict = create_folder_to_files_dictionary(cursor)
    is_subset = find_subset_statuses(folder_dict)
    max_folders = find_maximal_folders(is_subset)

    print("Maximal folders:")
    for folder in sorted(max_folders):
        print(folder)
    print(f"\nTotal maximal folders: {len(max_folders)}")
    print(f"\nTotal subset folders: {len([folder for folder, is_sub in is_subset.items() if is_sub])}")

    if args.remove:
        removed_count = remove_subset_entries(cursor, is_subset)
        conn.commit()
        print(f"\nRemoved {removed_count} entries from database.")

    if args.samples > 0:
        print_samples(cursor, is_subset, args.samples)

    if args.dry_run or args.charts_root:
        if not args.charts_root:
            print("Error: --charts-root required when using --dry-run or --move")
            return
            
        moved = move_folders(
            is_subset,
            charts_root=args.charts_root,
            dry_run=args.dry_run
        )
        
        backup_root = Path(args.charts_root).parent / f"{Path(args.charts_root).name}_bac"
        print(f"\nBackup location: {backup_root}")
        
        print("\nOperations:")
        for src, dest in moved:
            status = "Would move" if args.dry_run else "Moved"
            print(f"{status}: {src} -> {dest}")

    conn.close()

if __name__ == "__main__":
    main()
