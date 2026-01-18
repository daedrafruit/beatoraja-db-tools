import argparse
from pathlib import Path


def convert(root):
    for child in root.iterdir():
        if child.is_dir():
            convert(child)
        if child.suffix.lower() == ".wav":
            print(str(child.name))


def main():
    parser = argparse.ArgumentParser(description="Recursively batch convert .wav to .ogg using oggenc2 and ffmpeg as fallback")
    parser.add_argument("--path", required=True, help="Path to root")
    parser.add_argument("--q", required=True, help="Encoding quality")
    args = parser.parse_args()
    convert(Path(args.path))

if __name__ == "__main__":
    main()
