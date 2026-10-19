"""
1. Download XNB2PNG from https://github.com/tolik518/Xnb2png
2. Place XNB2PNG.exe at the root
3. Run extract_tiles.py and follow prompts
3a. Create xnbs/ folder if it doesn't already exist
3b. Place Tiles_*.xnb and/or Wall_*.xnb files from 'Terraria/Content/Images/' in xnbs/
4. Run extract_tiles.py to extract sprite sheets
"""

import pathlib
import os
import platform
import sys
from glob import glob
import subprocess
import shutil

def move_and_override(src: str, dst_folder: str) -> None:
    dst = pathlib.Path(src).relative_to(dst_folder, walk_up=True)
    if pathlib.Path(dst).exists():
        os.remove(dst)
    shutil.move(src, dst_folder)

def get_user_confirmation() -> bool:
    while True:
        result = input("Please confirm (y/n): ").lower()
        if result in ('y', 'yes', '1', 't', 'true'):
            return True
        elif result in ('n', 'no', '0', 'f', 'false'):
            return False
        print("Not a valid confirmation")

def ask_user_for_path() -> str:
    while True:
        result = input("Please enter a path: ")
        if pathlib.Path(result).exists():
            return result
        print("Not a valid path")

def pause_exit(code: int = 0):
    input("Press enter to continue...")
    sys.exit(code)

def try_get_steam_path() -> str | None:
    # Very roughly try to find steam location on windows
    # XNB2PNG is only for windows anyway
    if platform.system() != "Windows":
        return

    # Based on https://github.com/21-ko/SteamPathFinder
    import winreg

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "SOFTWARE\\Valve\\Steam")
        steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
        winreg.CloseKey(key)
    except FileNotFoundError:
        return # Is steam not installed?

    if not os.path.exists(steam_path):
        return # Steam path does not exist or is not accessible

    return steam_path

def glob_install_files(terraria_path: pathlib.Path) -> list[str]:
    tiles = []
    tiles.extend(glob(str(terraria_path / "Content/Images/Tiles_*.xnb")))
    tiles.extend(glob(str(terraria_path / "Content/Images/Wall_*.xnb")))
    return tiles
    
def try_get_steam_files() -> list[str] | None:
    steam_path = try_get_steam_path()
    if steam_path is None:
        return
    terraria_path = pathlib.Path(steam_path) / "steamapps/common/Terraria"
    if not terraria_path.exists():
        return

    tiles = glob_install_files(terraria_path)
    
    print(f"Detected terraria installation in your steam folder \"{steam_path}\", do you want to use it?")
    if not get_user_confirmation():
        return

    return tiles

def try_get_xnbs() -> list[str]:
    xnbs = try_get_steam_files()

    if xnbs is None:
        print("Terraria steam installation was not found...\n")
        print("Do you want to provide the file path to the terraria installation folder?")
        if not get_user_confirmation():
            print("Please manually provide xnb's in xnbs/")
            pause_exit(1)

        user_path = pathlib.Path(ask_user_for_path())
        if not (user_path / "Content/Images/").exists():
            print("Failed to confirm path, is that a terraria installation folder?")
            pause_exit(1)
        xnbs = glob_install_files(user_path)

    return xnbs

def convert(folder_name: str, name_prefix: str):
    sheets = glob(f"xnbs/{name_prefix}_*.png")
    if (len(sheets) > 0):
        pathlib.Path(folder_name).mkdir(exist_ok=True)

        # Clear folder
        old_tiles = glob(f"{folder_name}/{name_prefix}_*.png")
        for old_sheet in old_tiles:
            os.remove(old_sheet)

        for sheet in sheets:
            move_and_override(sheet, folder_name)
            print(sheet)


if __name__ == "__main__":
    # Make sure xnb2png exists
    if not pathlib.Path("XNB2PNG.exe").exists():
        print("Please provide XNB2PNG.exe from https://github.com/tolik518/Xnb2png", file=sys.stderr)
        input("Press enter to continue...")
        if not pathlib.Path("XNB2PNG.exe").exists():
            pause_exit(1)
        print("Found XNB2PNG.exe")
    # Make sure xnbs folder exists
    pathlib.Path("xnbs").mkdir(exist_ok=True)

    # Do we already have xnb's?
    xnbs = glob("xnbs/*.xnb")
    # No xnb files found
    if len(xnbs) == 0:
        xnbs = try_get_xnbs()
        for file in xnbs:
            shutil.copy(file, "xnbs/")
            print(f"Copied {file}")

    # Clean out old images
    files = glob("xnbs/*.png")
    for file in files:
        os.remove(file)
    # Convert xnbs to images
    subprocess.run(["XNB2PNG.exe", "."], cwd="xnbs")

    convert("terraria_blocks", "Tiles")
    convert("terraria_walls", "Wall")

    pause_exit()