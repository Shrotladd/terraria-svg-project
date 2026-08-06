My program to generate svg images for the https://terraria.wiki.gg/wiki/Blocks and https://terraria.wiki.gg/wiki/Background_walls wiki page's

# Todo:
- [ ] Correctly render lava clouds
- [ ] Correctly render rainbow boulder
- [ ] Language translations

# Dependencies:
- At least python 3.10
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

3. Run generate.py.
Pass -m block/wall to specify which svg to generate, by default it is -m block. -l to set the language, en by default. Pass -h to see options

4. Reference.svg should be created
