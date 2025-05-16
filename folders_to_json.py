import sqlite3
import json
from pathlib import Path
from collections import defaultdict
import argparse

def find_containing_child(parent_path, child_path):
    """Returns immediate child folder name or None"""
    parent_path = Path(parent_path).resolve()
    child_path = Path(child_path).resolve()
    
    try:
        if parent_path not in child_path.parents:
            return None
        return child_path.relative_to(parent_path).parts[0]
    except ValueError:
        return None

def create_category_mapping(database, charts_dir):
    """Create {category: [{"sha256":..., "title":..., "artist":...}, ...]}"""
    database.execute("SELECT md5, sha256, path, title, artist FROM song")
    charts_path = Path(charts_dir).resolve()
    category_map = defaultdict(list)
    
    for md5, sha256, path, title, artist in database.fetchall():
        if not path:
            continue
            
        category = find_containing_child(charts_path, path) or "Uncategorized"
        
        resolved_path = Path(path).resolve()
        song_title = title.strip() if title else resolved_path.parent.name
        
        song_artist = artist.strip() if artist else ""
        
        category_map[category].append({
            "title": song_title,
            "artist": song_artist,
            "sha256": sha256,
            "md5": md5
        })
    
    return dict(category_map)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create categorized BMS chart index"
    )
    parser.add_argument("--db", required=True, help="Path to song.db")
    parser.add_argument("--charts", required=True, help="Root BMS charts directory")
    parser.add_argument("--output", default="bms_index.json", help="Output JSON file")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    result = create_category_mapping(cursor, args.charts)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    conn.close()
