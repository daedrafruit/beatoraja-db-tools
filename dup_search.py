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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze and manage duplicate folders in a beatoraja database.")
    parser.add_argument("db_path", help="Path to song.db")
    parser.add_argument("--samples", type=int, default=0, help="Print out a number of sample hashes to analyze")
    parser.add_argument("--remove", action="store_true", help="Remove redundant entries from the database, not from disk")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db_path)
    cursor = conn.cursor()

    #folder_dict = create_folder_to_files_dictionary(cursor)
    #is_subset = find_subset_statuses(folder_dict)
    #max_folders = find_maximal_folders(is_subset)

    #charts = "C:/Users/dragonfruit/ma-crib/games/bms/charts"
    charts = "C:/Users/dragonfruit/ma-crib/games/bms/beatoraja/dup_search/test-charts"
    result = create_tables(cursor, charts)
    print(result)
    """
    print("Maximal folders:")
    for folder in sorted(max_folders):
        print(folder)
    print(f"\nTotal maximal folders: {len(max_folders)}")

    if args.remove:
        removed_count = remove_subset_entries(cursor, is_subset)
        conn.commit()
        print(f"\nRemoved {removed_count} entries from database.")

    if args.samples > 0:
        print_samples(cursor, is_subset, args.samples)
    """

    conn.close()
