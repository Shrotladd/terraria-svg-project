
import time
start_time = time.time()

import io
import sys
from enum import Enum
from dataclasses import dataclass
import pathlib
import math
from base64 import b64encode
import argparse

from PIL import Image
import uharfbuzz as hb
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
# from fontTools.pens.transformPen import TransformPen
# from fontTools.misc.transform import Transform 

import data
from data import Lang

parser = argparse.ArgumentParser()

parser.add_argument(
    "-m", "--mode", help="Which kind of svg to generate",
    default="block", choices=["block", "wall"])
parser.add_argument(
    "--debug_save_sections", default=False, help="Save constructed block images to \"{block/wall}_sections/\"",
    action=argparse.BooleanOptionalAction)
parser.add_argument(
    "--embed_font", default=False, help="Save's space and allows for selectable text, WARNING currently wiki.gg flags the file as unsafe when used, off by default",
    action=argparse.BooleanOptionalAction)
parser.add_argument(
    "-l", "--lang", help="Which language to generate",
    default=Lang.en.name, choices=Lang.names())

args = parser.parse_args(sys.argv[1:])

data.BLOCK_MODE = True if args.mode == "block" else False
data.DEBUG_SAVE_BLOCK_SECTIONS = args.debug_save_sections
data.EMBED_FONT_IN_SVG = args.embed_font
data.LANGUAGE = Lang[args.lang]
if data.EMBED_FONT_IN_SVG:
    print("- Embedding font enabled")

from data import (
    LayoutBehaviour, RenderedSection, ImageType,
    TILE_SIZE, FONT_SIZE, TERRARIA_FONT_NAME, TERRARIA_FONT,
    BLOCK_MODE, DEBUG_SAVE_BLOCK_SECTIONS, EMBED_FONT_IN_SVG, LANGUAGE, # Import BLOCK_MODE, etc *AFTER* parsing args
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
class CodepointInfo:
    gid: int
    x_advance: float
    y_advance: float

@dataclass
class SVGText:
    x: int
    y: int
    text: str | list[CodepointInfo]

    def encode(self, indent: Indenter) -> str:
        if isinstance(self.text, str):
            return f'{indent}<text x="{self.x}" y="{self.y}">{self.text}</text>\n' 
        out = ''
        x = self.x
        y = self.y
        for codepoint_info in self.text:
            out += f'{indent}<use href="#{codepoint_info.gid}" x="{x:.2f}" y="{y:.2f}"/>\n'
            x += codepoint_info.x_advance
            y += codepoint_info.y_advance
        return out

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
    font: TTFont
    used_glyphs: set[int]
    font_options: subset.Options
    background: SVGRect
    blocks: list[SVGGroup]

    def encode_embedded_font(self, indent: Indenter) -> str:
        # Write font style
        out = (
            f'{indent}<style>\n'
            f'{indent}@font-face {'{'}\n'
        )
        with indent:
            out += (
                f'{indent}font-family: "{self.font_family}";\n'
                f'{indent}src:\n'
            )
            with indent:
                out += (
                    f'{indent}url(data:font/{self.font_options.flavor};base64,{str(b64encode(self.font_to_data().getvalue()), encoding='utf-8')});\n'
                    f'{indent}format("{self.font_options.flavor}");\n'
                )
        out += (
            f'{indent}{'}'}\n'
            f'{indent}text {'{'}\n'
        )
        with indent:
            out += (
                f'{indent}font-family: "{self.font_family}";\n'
                f'{indent}font-size: {self.font_size}px;\n'
            )
        out += (
            f'{indent}{'}'}\n'
            f'{indent}</style>\n'
        )
        return out

    def font_to_data(self) -> io.BytesIO:
        font_data = io.BytesIO()
        subset.save_font(self.font, font_data, self.font_options)
        return font_data

    def encode_text_paths(self, indent: Indenter) -> str:
        glyph_set = self.font.getGlyphSet()
        glyph_order = self.font.getGlyphOrder()
        cmap = self.font.getBestCmap()

        # Assume the font contains character-to-glyph-index map
        assert(cmap is not None)


        scale: float = FONT_SIZE / self.font["head"].unitsPerEm # type: ignore
        paths = ''
        paths += f"{indent}<g style=\"display: none;\">\n"  # Hide them since they shouldn't be rendered
        with indent:
            for glyph_id in self.used_glyphs:
                try:
                    glyph_name = glyph_order[glyph_id]
                except:
                    continue
                glyph = glyph_set[glyph_name]
                pen = SVGPathPen(glyph_set)
                # transform_pen = TransformPen(pen, Transform().scale(x=scale, y=scale))
                glyph.draw(pen)
                paths += f'{indent}<path id="{glyph_id}" transform="scale({scale},-{scale})" d="{pen.getCommands()}"/>\n'
        paths += f"{indent}</g>"
        return paths

    def encode(self) -> str:
        out = ''
        indent = Indenter()

        # Write header
        out += (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg width="{self.width}" height="{self.height}" xmlns="http://www.w3.org/2000/svg">\n'
        )
        # Main body
        with indent:

            if EMBED_FONT_IN_SVG:
                out += self.encode_embedded_font(indent)
            else:
                out += self.encode_text_paths(indent)

            # Background rect
            out += self.background.encode(indent)

            # Make sure pngs use nearest neighbor
            out += f'{indent}<g image-rendering="optimizeSpeed" style="image-rendering:pixelated">\n'

            # Blocks and text
            with indent:
                for block_group in self.blocks:
                    out += block_group.encode(indent)
            
            out += f'{indent}</g>\n'

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

def write_svg(lang: Lang, rendered_blocks: dict[Enum, list[RenderedSection]]) -> None:

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
                for line in block_data.name.get(lang).splitlines():
                    glyph_infos, glyph_positions = shape_text(font, line)
                    text = SVGText(
                        x = int(x + text_x_offset),
                        y = int(y + text_y_offset),
                        text = line if EMBED_FONT_IN_SVG else [],
                    )
                    
                    for info, pos in zip(glyph_infos, glyph_positions):
                        gid = info.codepoint
                        used_glyphs.add(gid)
                        xadv = pos.x_advance * scale
                        yadv = pos.y_advance * scale
                        x += xadv
                        y += yadv
                        if not EMBED_FONT_IN_SVG:
                            assert(isinstance(text.text, list))
                            text.text.append(CodepointInfo(
                                gid=gid, x_advance=xadv, y_advance=yadv
                            ))

                    svg_lines.append(text)

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


    subset_options = subset.Options()
    # Convert font to woff2
    subset_options.flavor = "woff2"  # type: ignore
    subset_options.layout_features = ["*"]
    subset_options.desubroutinize = True
    subsetted_font = TTFont(io.BytesIO(font_data))
    if EMBED_FONT_IN_SVG:
        subsetter = subset.Subsetter()
        subsetter.populate(gids=used_glyphs)
        subsetter.subset(subsetted_font)

    w, h = int(max_x + SIDE_PADDING), int(max_y + SIDE_PADDING)

    svg_document = SVGDocument(
        width = w, height = h,
        font_family=TERRARIA_FONT_NAME,
        font=subsetted_font,
        font_options=subset_options,
        used_glyphs=used_glyphs,
        font_size=FONT_SIZE,
        background=SVGRect(
            width=w, height=h, fill="#fff"
        ),
        blocks = groups,
    )

    with open('Reference.svg', 'w', newline='') as file:
        file.write(svg_document.encode())

def process(lang: Lang) -> None:
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
                    print(f"Doing {block.name.get(lang)} prepass")
                except KeyError:
                    pass
                
                render = Meta.render_block(img, block, lut) # type: ignore

                if not category in file_dict:
                    file_dict[category] = []
                file_dict[category].append(render)

    print("Writing svg")
    write_svg(lang, file_dict) # type: ignore

if __name__ == "__main__":
    if DEBUG_SAVE_BLOCK_SECTIONS:
        render_path = pathlib.Path(Meta.rendered_image_folder_path())
        if not render_path.exists():
            print(f"Creating {render_path}")
            render_path.mkdir()
    
    process(lang=LANGUAGE)

    end_time = time.time()
    print(f"Finished in {end_time - start_time:.2f} seconds")
