
import time
start_time = time.time()

import io
import sys
from typing import Sequence
from enum import Enum, auto
from dataclasses import dataclass
import pathlib
import math

from PIL import Image
import numpy as np
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

from data import (
    LayoutBehaviour, RenderedSection,
    TILE_SIZE, FONT_SIZE, DEBUG_SAVE_BLOCK_SECTIONS, TERRARIA_FONT, BLOCK_MODE
)

# import blocks_meta as meta
if BLOCK_MODE:
    from blocks_meta import BlockMetadata as Meta
    from blocks_meta import Category
else:
    from walls_meta import WallMetadata as Meta
    from walls_meta import Category


def get_text_paths(tt_font: TTFont, used_glyphs: set[int]) -> str:
    glyph_set = tt_font.getGlyphSet()
    glyph_order = tt_font.getGlyphOrder()
    cmap = tt_font.getBestCmap()

    # Assume the font contains character-to-glyph-index map
    assert(cmap is not None)

    scale: float = FONT_SIZE / tt_font["head"].unitsPerEm # type: ignore
    defs_str = ''
    for glyph_id in used_glyphs:
        glyph_name = glyph_order[glyph_id]
        glyph = glyph_set[glyph_name]
        pen = SVGPathPen(glyph_set)
        glyph.draw(pen)
        defs_str += f'  <path id="{glyph_id}" transform="scale({scale},-{scale})" d="{pen.getCommands()}"/>\n'
    return defs_str

def shape_text(font, text: str):
    """Get harfbuzz text shape info, returns (hhb.Buffer.glyphs_infos, hb.Buffer.glyph_positions)"""
    features = {"kern": True, "liga": True}

    buf = hb.Buffer() # type: ignore
    buf.add_str(text)
    buf.guess_segment_properties()

    hb.shape(font, buf, features) # type: ignore

    infos = buf.glyph_infos
    positions = buf.glyph_positions

    return infos, positions

def write_svg(rendered_blocks: dict[Enum, list[RenderedSection]]) -> None:
    max_x = 0
    max_y = 0
    text_str = ''
    img_str = '  <g image-rendering="optimizeSpeed" style="image-rendering:pixelated">\n'

    try:
        with open(TERRARIA_FONT, 'rb') as f:
            font_data = f.read()
    except FileNotFoundError as e:
        print("Couldn't find font file, please follow the README to download.")
        input("Press anykey to continue...")
        sys.exit(1)
    
    used_glyphs: set[int] = set()

    offsets = Meta.get_layout_offsets()
    
    tt_font = TTFont(io.BytesIO(font_data))
    face = hb.Face(font_data) # type: ignore
    font = hb.Font(face) # type: ignore

    upem = face.upem
    font.scale = (upem, upem)
    scale = FONT_SIZE / upem

    col = 0
    SIDE_PADDING = 6
    for column_info in Meta.get_category_layout_info():
        do_x_offset = False
        row = 0
        for category_layout in column_info.categories:
            category = category_layout.category
            layout = category_layout.layout

            try:
                blocks_ls = rendered_blocks[category]
            except KeyError:
                print(f"Error: Missing category {category} in rendered_blocks")
                continue

            for i, block in enumerate(blocks_ls):
                # Place blocks
                block_data = Meta.get_tile_dictionary()[category][i] # type: ignore

                # x = col * 325 + 6 + 16
                x = col + SIDE_PADDING
                size = block_data.section_final_size()# * 8 * SHEET_SCALE
                match layout:
                    case LayoutBehaviour.ALTERNATING:
                        block_x = x + (TILE_SIZE if do_x_offset else 0)
                        do_x_offset = not do_x_offset
                    case LayoutBehaviour.CENTER:
                        block_x = x - math.floor(size[0] / 2) + TILE_SIZE * 2

                y = row * TILE_SIZE + SIDE_PADDING

                img_str += (
                    f'    <image x="{block_x}" y="{y}" width="{size[0]}" height="{size[1]}" '
                    f'href="data:image/{block.image_type.name.lower()};base64,{str(block.data, encoding="utf-8")}"/>\n'
                )
                
                # Place text
                start_x = x
                lines = block_data.name.splitlines()
                text_x_offset = offsets.text_x_offset
                text_y_offset = offsets.text_y_offset
                for line in lines:
                    glyph_infos, glyph_positions = shape_text(font, line)
                    for info, pos in zip(glyph_infos, glyph_positions):
                        gid = info.codepoint
                        used_glyphs.add(gid)
                        text_str += (
                            f'  <use href="#{gid}" '
                            f'x="{x + text_x_offset}" '
                            f'y="{y + text_y_offset}"/>\n'
                        )
                        x += pos.x_advance * scale
                        y += pos.y_advance * scale
                    max_x = max(max_x, x + text_x_offset)
                    max_y = max(max_y, y + text_y_offset + size[1] / 2)
                    x = start_x
                    y += FONT_SIZE
                row += offsets.row_advance
            # Space categories a little bit
            row += offsets.category_advance
        col += column_info.x_offset_to_next
    img_str += '  </g>\n'

    # w and h use similar math to get x and y position of tiles in svg
    w, h = max_x + SIDE_PADDING, max_y + SIDE_PADDING

    with open('output.svg', 'w', newline='') as file:
        # Header
        file.write(
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink">\n'
        )
        # Precomputed paths
        file.write(get_text_paths(tt_font, used_glyphs))
        # Background
        file.write(f'  <rect width="{w}" height="{h}" fill="#fff"/>\n')
        # Image data
        file.write(img_str)
        # References to precomputed paths and where to put them
        file.write(text_str)

        file.write('</svg>\n')


def process() -> None:
    file_dict: dict[Category, list[RenderedSection]] = {}

    for category, block_list in Meta.get_tile_dictionary().items():
        for block in block_list:
            tile_image_path: str = Meta.get_block_path(block.tile_number)
            # Assume images exist
            with Image.open(tile_image_path) as img:
                lut = Meta.get_template_and_lut(block.pattern) # type: ignore

                try:
                    Meta.get_tile_img_prepasses()[block.tile_number](img)
                except KeyError:
                    pass

                render = Meta.render_block(img, block, lut) # type: ignore

                if not category in file_dict:
                    file_dict[category] = []
                file_dict[category].append(render)

    write_svg(file_dict) # type: ignore

if __name__ == "__main__":
    if DEBUG_SAVE_BLOCK_SECTIONS:
        pathlib.Path(Meta.rendered_image_folder_path()).mkdir(exist_ok=True)
    
    process()

    end_time = time.time()
    print(f"Finished in {end_time - start_time:.2f} seconds")