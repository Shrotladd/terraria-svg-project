
import time
start_time = time.time()

import io
import sys
from enum import Enum
import pathlib
import math
import argparse

import PIL.Image
import uharfbuzz as hb
from fontTools import subset
from fontTools.ttLib import TTFont

import svg

from data import (
    Lang, LayoutBehaviour, RenderedSection, Options, Metadata,
    TILE_SIZE, FONT_SIZE,
)


def write_svg(options: Options, rendered_blocks: dict[Enum, list[RenderedSection]], meta: Metadata) -> None:

    try:
        with open(options.get_font_path(), 'rb') as f:
            font_data = f.read()
    except FileNotFoundError as e:
        print("Couldn't find font file, please follow the README to download.")
        input("Press anykey to continue...")
        sys.exit(1)
    
    used_glyphs: set[int] = set()

    offsets = meta.get_layout_offsets()
    
    face = hb.Face(font_data) # type: ignore
    font = hb.Font(face) # type: ignore

    upem = face.upem
    font.scale = (upem, upem)
    scale = FONT_SIZE / upem

    SIDE_PADDING = 6
    col_x = 0

    group_columns: list[svg.Column] = []
    max_x: int = 0
    max_y: int = 0

    def get_tuck_x(current_column: int, height: int) -> int:
        # Allow for auto aligning of columns accounting for the length of block language strings
        nonlocal group_columns
        x = 0
        if current_column == 0: # The first column
            return x
        col = group_columns[current_column - 1]
        for row in col.groups:
            if row.y > height:
                break
            x = max(x, row.max_width)
        return x
    
    for column_index, column_info in enumerate(meta.get_category_layout_info()):
        do_x_offset = False
        row = 0
        column_height = 0
        column_width = 0
        group_column = svg.Column(start_x=0, groups=[])
        for category_layout in column_info:
            category = category_layout.category

            try:
                blocks_ls = rendered_blocks[category]
            except KeyError:
                print(f"Error: Missing category {category} in rendered_blocks")
                continue

            # Place blocks
            for i, block in enumerate(blocks_ls):
                block_data = meta.get_tile_dictionary()[category][i]

                x = col_x
                size = block_data.section_final_size()
                x_offset = 0
                match category_layout.layout:
                    case LayoutBehaviour.ALTERNATING:
                        x_offset = TILE_SIZE if do_x_offset else 0
                        do_x_offset = not do_x_offset
                    case LayoutBehaviour.CENTER:
                        x_offset = -math.floor(size[0] / 2) + TILE_SIZE * 2
                        
                y: int = row * TILE_SIZE

                img = svg.Image(
                    x_offset = x_offset,
                    y = y + SIDE_PADDING,
                    width = size[0],
                    height = size[1],
                    image_type = block.image_type,
                    data = block.data,
                )

                # Place text
                text_x_offset = int(offsets.text_x_offset)
                text_y_offset = int(offsets.text_y_offset)

                svg_lines, text_max_x, text_max_y = svg.get_svg_text(
                    block_data, font, options.language, used_glyphs,
                    text_x_offset,
                    y, text_y_offset + SIDE_PADDING,
                    scale,
                    options.embed_font_in_svg)

                column_width = max(column_width, text_max_x + TILE_SIZE)
                max_x = max(max_x, x + column_width)
                max_y = max(max_y, y + text_max_y + size[1] // 2)

                row += offsets.row_advance
                column_height = y
                group_column.groups.append(svg.Row(
                    image=img, lines=svg_lines,
                    max_width=column_width, y=y))
                
            # Space categories a little bit
            row += offsets.category_advance
        col_x += get_tuck_x(column_index, column_height)
        max_x = max(max_x, col_x + column_width)
        group_column.start_x = col_x + SIDE_PADDING
        group_columns.append(group_column)

    subset_options = subset.Options()
    # Convert font to woff2
    subset_options.flavor = "woff2"  # type: ignore
    subset_options.layout_features = ["*"]
    subset_options.desubroutinize = True
    subsetted_font = TTFont(io.BytesIO(font_data))
    if options.embed_font_in_svg:
        subsetter = subset.Subsetter()
        subsetter.populate(gids=used_glyphs)
        subsetter.subset(subsetted_font)

    svg_document = svg.Document(
        width = max_x, height = max_y,
        font_family=options.font_name,
        font=subsetted_font,
        font_options=subset_options,
        used_glyphs=used_glyphs,
        font_size=FONT_SIZE,
        background=svg.Rect(
            width=max_x, height=max_y, fill="#fff"
        ),
        blocks = group_columns,
        embed_font=options.embed_font_in_svg
    )

    with open('Reference.svg', 'w', newline='') as file:
        file.write(svg_document.encode())


def process(options: Options, meta: Metadata) -> None:
    file_dict = {}
    print("Rendering")
    for category, block_list in meta.get_tile_dictionary().items():
        for block in block_list:
            tile_image_path: str = meta.get_block_path(block.tile_number)
            # Assume images exist
            with PIL.Image.open(tile_image_path) as img:
                lut = meta.get_template_and_lut(block.pattern)

                try:
                    meta.get_tile_img_prepasses()[block.tile_number](img)
                    print(f"Doing {block.name.get(options.language)} prepass")
                except KeyError:
                    pass
                
                render = meta.render_block(img, block, lut, options.debug_save_block_sections)

                if not category in file_dict:
                    file_dict[category] = []
                file_dict[category].append(render)

    print("Writing svg")
    write_svg(options, file_dict, meta)


def get_options() -> tuple[Metadata, Options]:
    parser = argparse.ArgumentParser()
    
    import blocks_meta
    import walls_meta
    mode_choices = {
        "block": blocks_meta.BlockMetadata,
        "wall": walls_meta.WallMetadata,
    }

    parser.add_argument(
        "-m", "--mode", help="Which kind of svg to generate",
        required=True, choices=mode_choices.keys())
    parser.add_argument(
        "--debug_save_sections", default=False, help="Save constructed block images to \"{block/wall}_sections/\"",
        action=argparse.BooleanOptionalAction)
    parser.add_argument(
        "--embed_font", default=False, help="Save's space and allows for selectable text, WARNING currently wiki.gg flags the file as unsafe when used, off by default",
        action=argparse.BooleanOptionalAction)
    parser.add_argument(
        "-l", "--lang", help="Which language to generate",
        default=Lang.en.name, choices=Lang.names())
    parser.add_argument(
        "-f", "--font", help="The font file to use when writing svg",
        default="Andy Std Bold.otf"
    )

    args = parser.parse_args(sys.argv[1:])
    if args.mode not in mode_choices:
        print(f"Unknown generator mode: {args.mode}")
        sys.exit(1)

    font = pathlib.Path(args.font)
    if not font.exists():
        print("Couldn't find font file")
        sys.exit(1)

    meta = mode_choices[args.mode]
    options = Options(
        debug_save_block_sections = args.debug_save_sections,
        embed_font_in_svg = args.embed_font,
        language = Lang[args.lang],
        font_folder = font.parent,
        font_name = font.stem,
        font_ext = font.suffix,
    )

    print(f"- Using \"{options.font_name}\" font")

    if options.embed_font_in_svg:
        print("- Embedding font enabled")

    return meta, options


if __name__ == "__main__":
    meta, options = get_options()

    if options.debug_save_block_sections:
        render_path = pathlib.Path(meta.rendered_image_folder_path())
        if not render_path.exists():
            print(f"Creating {render_path}")
            render_path.mkdir()
    
    process(options, meta)

    end_time = time.time()
    print(f"Finished in {end_time - start_time:.2f} seconds")
