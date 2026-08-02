"""
1. Download XNB2PNG from https://github.com/tolik518/Xnb2png
2. Place XNB2PNG.exe at the root
3a. Create xnbs/ folder if it doesn't already exist
3b. Place Tiles_*.xnb and/or Wall_*.xnb files from 'Terraria/Content/Images/' in xnbs/
4. Run extract_tiles.py to extract sprite sheets
"""

DRY_RUN: bool = False

import pathlib
import os
import sys
from glob import glob
import subprocess
import shutil

def move_and_override(src: str, dst_folder: str) -> None:
    dst = pathlib.Path(src).relative_to(dst_folder, walk_up=True)
    if pathlib.Path(dst).exists():
        os.remove(dst)
    shutil.move(src, dst_folder)

if __name__ == "__main__":
    # Make sure xnb2png exists
    if not pathlib.Path("XNB2PNG.exe").exists():
        print("Please provide XNB2PNG.exe from https://github.com/tolik518/Xnb2png", file=sys.stderr)
        input("Press any key to continue...")
        sys.exit(1)

    xnbs = glob("xnbs/*.xnb")

    if not DRY_RUN:
        files = glob("xnbs/*.png")
        for file in files:
            os.remove(file)
        subprocess.run(["XNB2PNG.exe", "."], cwd="xnbs")

    tile_sheets = glob("xnbs/Tiles_*.png")
    if (len(tile_sheets) > 0):
        pathlib.Path("terraria_blocks").mkdir(exist_ok=True)

        # Clear folder
        if not DRY_RUN:
            old_tiles = glob("terraria_blocks/Tiles_*.png")
            for old_sheet in old_tiles:
                os.remove(old_sheet)

        for sheet in tile_sheets:
            if not DRY_RUN:
                move_and_override(sheet, "terraria_blocks")
            print(sheet)
    
    wall_sheets = glob("xnbs/Wall_*.png")
    if (len(wall_sheets) > 0):
        pathlib.Path("terraria_walls").mkdir(exist_ok=True)

        # Clear folder
        if not DRY_RUN:
            old_tiles = glob("terraria_walls/Wall_*.png")
            for old_sheet in old_tiles:
                os.remove(old_sheet)

        for sheet in wall_sheets:
            if not DRY_RUN:
                move_and_override(sheet, "terraria_walls")
            print(sheet)