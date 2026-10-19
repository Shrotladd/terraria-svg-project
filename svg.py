from dataclasses import dataclass
import io
from base64 import b64encode

from fontTools.ttLib import TTFont
from fontTools import subset
from fontTools.pens.svgPathPen import SVGPathPen
import uharfbuzz as hb

from data import ImageType, Lang, FONT_SIZE


class Indenter:
    def __init__(self, indents: int = 0, indent_spaces: int = 2) -> None:
        self.indent = indents
        self.indent_spaces = indent_spaces

    def __enter__(self):
        self.indent += 1
        return self

    def __exit__(self, exc_type, exc, tb):
        self.indent -= 1

    def __repr__(self) -> str:
        return ' ' * self.indent * self.indent_spaces


@dataclass
class Image:
    x_offset: int
    y: int
    width: int
    height: int
    image_type: ImageType
    data: bytes

    def encode(self, start_x: int, indent: Indenter) -> str:
        return (
            f'{indent}<image x="{start_x + self.x_offset}" y="{self.y}" width="{self.width}" height="{self.height}" '
            f'href="data:image/{self.image_type.name.lower()};base64,{str(self.data, encoding="utf-8")}"/>\n'
        )


@dataclass
class CodepointInfo:
    gid: int
    x_advance: float
    y_advance: float


@dataclass
class Text:
    x_offset: int
    y: int
    text: str | list[CodepointInfo]

    def encode(self, start_x: int, indent: Indenter) -> str:
        if isinstance(self.text, str):
            return f'{indent}<text x="{start_x + self.x_offset}" y="{self.y}">{self.text}</text>\n' 
        out = ''
        x = float(start_x + self.x_offset)
        y = self.y
        for codepoint_info in self.text:
            out += f'{indent}<use href="#{codepoint_info.gid}" x="{x:.2f}" y="{y:.2f}"/>\n'
            x += codepoint_info.x_advance
            y += codepoint_info.y_advance
        return out


@dataclass
class Row:
    image: Image
    lines: list[Text]
    max_width: int  # Width of the current group
    y: int  # Y position of the current group

    def encode(self, start_x: int, indent: Indenter) -> str:
        out = ''
        for line in self.lines:
            out += line.encode(start_x, indent)
        out += self.image.encode(start_x, indent)
        return out


@dataclass
class Rect:
    width: int
    height: int
    fill: str

    def encode(self, indent: Indenter) -> str:
        return f'{indent}<rect width="{self.width}" height="{self.height}" fill="{self.fill}"/>\n'


@dataclass
class Column:
    start_x: int
    groups: list[Row]


@dataclass
class Document:
    width: int
    height: int
    font_family: str
    font_size: int
    font: TTFont
    used_glyphs: set[int]
    font_options: subset.Options
    background: Rect
    blocks: list[Column]
    embed_font: bool

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
        paths += f"{indent}</g>\n"
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

            if self.embed_font:
                out += self.encode_embedded_font(indent)
            else:
                out += self.encode_text_paths(indent)

            # Background rect
            out += self.background.encode(indent)

            # Make sure pngs use nearest neighbor
            out += f'{indent}<g image-rendering="optimizeSpeed" style="image-rendering:pixelated">\n'

            # Blocks and text
            with indent:
                for col in self.blocks:
                    for group in col.groups:
                        out += group.encode(col.start_x, indent)
            
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


def get_svg_text(
        block, font, lang: Lang, used_glyphs: set[int],
        text_x_offset: int, text_y: float, text_y_offset: int, text_scale: float,
        embed_font_in_svg: bool
        ) -> tuple[list[Text], int, int]:
    """Get a list of lines and the local max_x and max_y"""
    svg_lines: list[Text] = []
    x = 0
    y = 0
    max_x: int = 0
    max_y: int = 0

    for line in block.name.get(lang).splitlines():
        glyph_infos, glyph_positions = shape_text(font, line)
        text = Text(
            x_offset = text_x_offset,
            y = int(y + text_y + text_y_offset),
            text = line if embed_font_in_svg else [],
        )
        for info, pos in zip(glyph_infos, glyph_positions):
            gid = info.codepoint
            used_glyphs.add(gid)
            xadv = pos.x_advance * text_scale
            yadv = pos.y_advance * text_scale
            x += xadv
            y += yadv
            if not embed_font_in_svg:
                assert(isinstance(text.text, list))
                text.text.append(CodepointInfo(
                    gid=gid, x_advance=xadv, y_advance=yadv
                ))
        svg_lines.append(text)
        max_x = max(max_x, int(x + text_x_offset))
        max_y = max(max_y, int(y + text_y_offset))
        x = 0
        y += FONT_SIZE
    return svg_lines, max_x, max_y
