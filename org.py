

import os
import re
import shutil
import argparse

DATA_DIR = r"D:\Data"

# Matches things like:
#   N020-V001, N031_V002, M01_V001, S01-V007
# Group 1 = prefix (letters + digits, e.g. "N020", "M01", "S01")
# Group 2 = video part (e.g. "V001")
NAME_PATTERN = re.compile(r"^([A-Za-z]+\d+)[-_]?(V\d+)$")


def find_misplaced_folders(data_dir):
    """
    Scans data_dir/*/keyframes/* and returns a list of
    (current_path, correct_top_folder, correct_video_name, correct_path)
    for any video folder that either:
      - sits under the wrong top-level folder, or
      - uses "-" instead of "_" (or any other mismatch vs the normalized name)
    """
    moves = []

    for top_folder in os.listdir(data_dir):
        top_path = os.path.join(data_dir, top_folder)
        if not os.path.isdir(top_path):
            continue

        kf_path = os.path.join(top_path, "keyframes")
        if not os.path.isdir(kf_path):
            continue

        for video_folder in os.listdir(kf_path):
            video_path = os.path.join(kf_path, video_folder)
            if not os.path.isdir(video_path):
                continue

            match = NAME_PATTERN.match(video_folder)
            if not match:
                print(f"[WARN] Skipping unrecognized folder name: {video_path}")
                continue

            prefix, vpart = match.group(1), match.group(2)
            correct_name = f"{prefix}_{vpart}"          # normalized, e.g. "N031_V001"
            correct_top = prefix                         # e.g. "N031"
            correct_path = os.path.join(data_dir, correct_top, "keyframes", correct_name)

            if video_path != correct_path:
                moves.append((video_path, correct_top, correct_name, correct_path))

    return moves


def apply_moves(moves, dry_run=True):
    for src, correct_top, correct_name, dst in moves:
        dst_parent = os.path.dirname(dst)

        if dry_run:
            print(f"[DRY RUN] Would move:\n  {src}\n  -> {dst}\n")
            continue

        if os.path.exists(dst):
            print(f"[SKIP] Destination already exists, not overwriting:\n  {dst}\n")
            continue

        os.makedirs(dst_parent, exist_ok=True)
        shutil.move(src, dst)
        print(f"[MOVED]\n  {src}\n  -> {dst}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=DATA_DIR, help="Root data directory")
    parser.add_argument("--apply", action="store_true",
                         help="Actually perform the moves. Without this flag, it's a dry run.")
    args = parser.parse_args()

    moves = find_misplaced_folders(args.data_dir)

    if not moves:
        print("Nothing to move — everything is already in the right place.")
        return

    print(f"Found {len(moves)} folder(s) to fix:\n")
    apply_moves(moves, dry_run=not args.apply)

    if not args.apply:
        print("\nThis was a dry run. Re-run with --apply to actually move the folders.")


if __name__ == "__main__":
    main()