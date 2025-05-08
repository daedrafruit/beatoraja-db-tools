import sqlite3
from pathlib import Path
from collections import defaultdict
import argparse

def create_folder_to_files_dictionary(database):
    """map each directory to its file hashes."""
    database.execute("SELECT sha256, path FROM song")
    dictionary = defaultdict(list)
    for sha256, path in database.fetchall():
        parent = str(Path(path).parent)
        dictionary[parent].append(sha256)
    return dictionary

def find_subset_statuses(folder_dict):
    """find folders that are subsets of others."""
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
    """feturn folder names that are not subsets of any other folder."""
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("db_path", help="Path to song.db")
    parser.add_argument("--samples", type=int, default=0, help="Number of sample hashes to analyze")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db_path)
    cursor = conn.cursor()

    folder_dict = create_folder_to_files_dictionary(cursor)
    is_subset = find_subset_statuses(folder_dict)
    max_folders = find_maximal_folders(is_subset)

    print("Maximal folders:")
    for folder in sorted(max_folders):
        print(folder)
    print(f"\nTotal maximal folders: {len(max_folders)}")

    if args.samples > 0:
        print_samples(cursor, is_subset, args.samples)

    conn.close()
