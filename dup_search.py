import sqlite3
from pathlib import Path
from collections import defaultdict
import argparse

def create_hash_to_folders_dictionary(database):
    """map each hash to all directories containing that file"""
    database.execute("SELECT sha256, path FROM song")
    dictionary = defaultdict(list)
    for sha256, path in database.fetchall():
        dictionary[sha256].append(str(Path(path).parent))
    return dictionary

def create_folder_to_files_dictionary(database):
    """map each directory to its file information"""
    database.execute("SELECT sha256, path FROM song")
    dictionary = defaultdict(list)
    for sha256, path in database.fetchall():
        parent = str(Path(path).parent)
        filename = Path(path).name.lower()
        dictionary[parent].append({'name': filename, 'hash': sha256})
    return dictionary

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("db_path", help="Path to song.db")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db_path)
    database = conn.cursor()
    
    hash_to_folders = create_hash_to_folders_dictionary(database)
    folder_dictionary = create_folder_to_files_dictionary(database)

    chart_hash = '0001cb22e849ad8d6622403b0f911b08db617b6c82438654593a5ac73cf06dda'
    song_dirs = hash_to_folders.get(chart_hash, [])

    for song_dir in song_dirs:
        charts = folder_dictionary.get(song_dir, [])
        
        print(f"Song found at: {song_dir}")
        print(f"Charts: {len(charts)}")
        print("Chart hashes:")
        for chart in charts:
            print(f"  {chart['name']}: {chart['hash']}")
        print("-" * 40)


