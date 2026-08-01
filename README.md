My somewhat convoluted program to generate an svg image for the https://terraria.wiki.gg/wiki/Blocks and https://terraria.wiki.gg/wiki/Background_walls wiki page

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
- https://fontsgeek.com/fonts/Andy-Std-Bold, place .otf file at the root
- Correctly named tile map files. Follow instructions in extract_tiles.py

# Instructions:

1. > git clone https://github.com/Shrotladd/terraria-svg-project

2. Acquire dependencies

3. In data.py change BLOCK_MODE to True to generate block's svg or False to generate wall svg

3. Run terraria_blocks_project.py *Optional*: You can set DEBUG_SAVE_BLOCK_SECTIONS in terraria_blocks_project.py to True to dump rendered png/gif files to sections/

4. ouput.svg should be created 

