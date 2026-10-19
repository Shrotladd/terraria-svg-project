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

1. Download
> git clone https://github.com/Shrotladd/terraria-svg-project

2. Go into it
> cd terraria-svg-project

3. For cleanliness create an environment 
> python -m venv .venv

4. Enter created environment
- On windows `.venv/Scripts/Activate.ps1`
- On linux with bash `source .venv/bin/activate`

5. Acquire dependencies
- Install modules `pip install -r requirements.txt`
- Run `python extract_files.py` and follow prompts
- Download font file

6. Run
- `python generate.py -m block` to generate block svg
- `python generate.py -m wall` to generate wall svg
- Pass `-l <lang>` to set the language, en by default
- Pass `-f <font>` to set the current font
- Pass `-h` to see all options

7. `Reference.svg` should be created
