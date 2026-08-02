
import time
start_time = time.time()

import io
import sys
from enum import Enum
from dataclasses import dataclass, field
import pathlib
import math
from base64 import b64encode

from PIL import Image
import uharfbuzz as hb
from fontTools import subset
from fontTools.ttLib import TTFont

from data import (
    LayoutBehaviour, RenderedSection, ImageType,
    TILE_SIZE, FONT_SIZE, DEBUG_SAVE_BLOCK_SECTIONS, TERRARIA_FONT, BLOCK_MODE
)

# import blocks_meta as meta
if BLOCK_MODE:
    from blocks_meta import BlockMetadata as Meta
    from blocks_meta import Category
else:
    from walls_meta import WallMetadata as Meta
    from walls_meta import Category

class Indenter:
    def __init__(self, indents: int = 0, indent_spaces: int = 2) -> None:
        self.indent = indents
        self.indent_spaces = indent_spaces

    def __enter__(self):
        self.indent += self.indent_spaces
        return self

    def __exit__(self, exc_type, exc, tb):
        self.indent -= self.indent_spaces

    def __repr__(self) -> str:
        return ' ' * self.indent * self.indent_spaces
    
@dataclass
class SVGImage:
    x: int
    y: int
    width: int
    height: int
    image_type: ImageType
    data: bytes

    def encode(self, indent: Indenter) -> str:
        return (
            f'{indent}<image x="{self.x}" y="{self.y}" width="{self.width}" height="{self.height}" '
            f'href="data:image/{self.image_type.name.lower()};base64,{str(self.data, encoding="utf-8")}"/>\n'
        )

@dataclass
class SVGText:
    x: int
    y: int
    text: str

    def encode(self, indent: Indenter) -> str:
        return (
            f'{indent}<text '
            f'x="{self.x}" y="{self.y}">'
            f'{self.text}'
            '</text>\n'
        )

@dataclass
class SVGGroup:
    image: SVGImage
    lines: list[SVGText]

    def encode(self, indent: Indenter) -> str:
        out = ''
        # out += f'{indent}<g>\n'
        # with indent:
        for line in self.lines:
            out += line.encode(indent)
        out += self.image.encode(indent)
        # out += f'{indent}</g>\n'
        return out

@dataclass
class SVGRect:
    width: int
    height: int
    fill: str

    def encode(self, indent: Indenter) -> str:
        return f'{indent}<rect width="{self.width}" height="{self.height}" fill="{self.fill}"/>\n'

@dataclass
class SVGDocument:
    width: int
    height: int
    font_family: str
    font_size: int
    font_data: io.BytesIO
    background: SVGRect
    blocks: list[SVGGroup]

    indent: Indenter = field(default_factory=lambda: Indenter())

    def encode(self) -> str:
        out = ''

        # Write header
        out += (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg width="{self.width}" height="{self.height}" xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink">\n'
        )
        # Main body
        with self.indent:
            # Write font style
            out += (
                f'{self.indent}<style>\n'
                f'{self.indent}@font-face {'{'}\n'
            )
            with self.indent:
                out += (
                    f'{self.indent}font-family: "{self.font_family}";\n'
                    f'{self.indent}src:\n'
                )
                with self.indent:
                    out += (
                        f'{self.indent}url(data:font/woff2;charset=utf-8;base64,{str(b64encode(self.font_data.getvalue()), encoding='utf-8')});\n'
                        f'{self.indent}format("woff2");\n'
                    )
            out += (
                f'{self.indent}{'}'}\n'
                f'{self.indent}text {'{'}\n'
            )
            with self.indent:
                out += (
                    f'{self.indent}font-family: "{self.font_family}";\n'
                    f'{self.indent}font-size: {self.font_size}px;\n'
                )
            out += (
                f'{self.indent}{'}'}\n'
                f'{self.indent}</style>\n'
            )

            # Background rect
            out += self.background.encode(self.indent)

            # Make sure pngs use nearest neighbor
            out += f'{self.indent}<g image-rendering="optimizeSpeed" style="image-rendering:pixelated">\n'

            # Blocks and text
            with self.indent:
                for block_group in self.blocks:
                    out += block_group.encode(self.indent)
            
            out += f'{self.indent}</g>\n'

        out += '</svg>\n'
        
        return out

def shape_text(font, text: str):
    """Get harfbuzz text shape info, returns (hb.Buffer.glyphs_infos, hb.Buffer.glyph_positions)"""
    features = {"kern": True, "liga": True}

    buf = hb.Buffer() # type: ignore
    buf.add_str(text)
    buf.guess_segment_properties()

    hb.shape(font, buf, features) # type: ignore

    infos = buf.glyph_infos
    positions = buf.glyph_positions

    return infos, positions

def write_svg(rendered_blocks: dict[Enum, list[RenderedSection]]) -> None:

    try:
        with open(TERRARIA_FONT, 'rb') as f:
            font_data = f.read()
    except FileNotFoundError as e:
        print("Couldn't find font file, please follow the README to download.")
        input("Press anykey to continue...")
        sys.exit(1)
    
    used_glyphs: set[int] = set()

    offsets = Meta.get_layout_offsets()
    
    face = hb.Face(font_data) # type: ignore
    font = hb.Font(face) # type: ignore

    upem = face.upem
    font.scale = (upem, upem)
    scale = FONT_SIZE / upem

    col = 0
    SIDE_PADDING = 6

    groups: list[SVGGroup] = []
    max_x = 0
    max_y = 0
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

                x = col + SIDE_PADDING
                size = block_data.section_final_size()
                match layout:
                    case LayoutBehaviour.ALTERNATING:
                        block_x = x + (TILE_SIZE if do_x_offset else 0)
                        do_x_offset = not do_x_offset
                    case LayoutBehaviour.CENTER:
                        block_x = x - math.floor(size[0] / 2) + TILE_SIZE * 2

                y = row * TILE_SIZE + SIDE_PADDING

                img = SVGImage(
                    x = block_x,
                    y = y,
                    width = size[0],
                    height = size[1],
                    image_type = block.image_type,
                    data = block.data,
                )

                # Place text
                start_x = x
                text_x_offset = offsets.text_x_offset
                text_y_offset = offsets.text_y_offset

                svg_lines: list[SVGText] = []
                for line in block_data.name.splitlines():
                    glyph_infos, glyph_positions = shape_text(font, line)
                    svg_lines.append(SVGText(
                        x = int(x + text_x_offset),
                        y = int(y + text_y_offset),
                        text = line,
                    ))
                    for info, pos in zip(glyph_infos, glyph_positions):
                        gid = info.codepoint
                        used_glyphs.add(gid)
                        x += pos.x_advance * scale
                        y += pos.y_advance * scale
                    max_x = max(max_x, x + text_x_offset)
                    max_y = max(max_y, y + text_y_offset + size[1] / 2)
                    x = start_x
                    y += FONT_SIZE
                row += offsets.row_advance
                # text_ref_str += "  </g>\n"
                groups.append(SVGGroup(img, svg_lines))
            # Space categories a little bit
            row += offsets.category_advance
        col += column_info.x_offset_to_next


    subset_otions = subset.Options()
    subset_otions.flavor = "woff2"  # type: ignore
    subset_otions.layout_features = ["*"]
    subset_otions.desubroutinize = True
    subsetter = subset.Subsetter()
    subsetter.populate(gids=used_glyphs)
    subsetted_font = TTFont(io.BytesIO(font_data))
    subsetter.subset(subsetted_font)
    subsetted_font_data = io.BytesIO()
    subset.save_font(subsetted_font, subsetted_font_data, subset_otions)

    w, h = int(max_x + SIDE_PADDING), int(max_y + SIDE_PADDING)

    svg_document = SVGDocument(
        width = w, height = h,
        font_family='AndyStdBold',
        font_data=subsetted_font_data,
        font_size=FONT_SIZE,
        background=SVGRect(
            width=w, height=h, fill="#fff"
        ),
        blocks = groups,
    )

    with open('Reference.svg', 'w', newline='') as file:
        file.write(svg_document.encode())

def process() -> None:
    file_dict: dict[Category, list[RenderedSection]] = {}

    print("Rendering")
    for category, block_list in Meta.get_tile_dictionary().items():
        for block in block_list:
            tile_image_path: str = Meta.get_block_path(block.tile_number)
            # Assume images exist
            with Image.open(tile_image_path) as img:
                lut = Meta.get_template_and_lut(block.pattern) # type: ignore

                try:
                    Meta.get_tile_img_prepasses()[block.tile_number](img)
                    print(f"Doing {block.name} prepass")
                except KeyError:
                    pass
                
                render = Meta.render_block(img, block, lut) # type: ignore

                if not category in file_dict:
                    file_dict[category] = []
                file_dict[category].append(render)

    print("Writing svg")
    write_svg(file_dict) # type: ignore

if __name__ == "__main__":
    if DEBUG_SAVE_BLOCK_SECTIONS:
        render_path = pathlib.Path(Meta.rendered_image_folder_path())
        if not render_path.exists():
            print(f"Creating {render_path}")
            pathlib.Path(Meta.rendered_image_folder_path()).mkdir()
    
    process()

    end_time = time.time()
    print(f"Finished in {end_time - start_time:.2f} seconds")