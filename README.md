My program to generate svg images for the https://terraria.wiki.gg/wiki/Blocks and https://terraria.wiki.gg/wiki/Background_walls wiki page's

# Todo:
- [ ] Correctly render lava clouds
- [ ] Correctly render rainbow boulder

# Dependencies:
- Python 3.11
- Python modules:
  - pillow
  - numpy
  - uharfbuzz
  - fonttools
  - brotlicffi
- https://fontsgeek.com/fonts/Andy-Std-Bold, place .otf file at the root
- Correctly named tile map files. Follow instructions in extract_tiles.py

# Instructions:

1. > git clone https://github.com/Shrotladd/terraria-svg-project

2. Acquire dependencies

3. In data.py change BLOCK_MODE to True to generate block svg or False to generate wall svg. *Optionally* set DEBUG_SAVE_BLOCK_SECTIONS to True to dump rendered png/gif's to disk

3. Run generate.py

4. Reference.svg should be created
