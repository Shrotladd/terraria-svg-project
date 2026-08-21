"""
data.py holds general config information for the project,
blocks_meta.py and walls_meta.py hold layout information for blocks and walls respectively
"""

from typing import Sequence, Callable
from abc import abstractmethod
from enum import Enum, auto, unique
from dataclasses import dataclass
from typing import Protocol

from PIL import Image


# Dimensions in # of tiles
SHEET_TILES_X = 16
SHEET_TILES_Y = 15
SHEET_SCALE = 2
FONT_SIZE = 20

# Space between top left corner of tiles, should be greater than the tile size.
TILE_SPACE = SHEET_SCALE * 9
TILE_SIZE = SHEET_SCALE * 8


# ---- Data classes ----

@unique
class Lang(Enum):
    en = auto()  # English
    # fr = auto()  # French
    # pt = auto()  # Portuguese
    # ru = auto()  # Russian
    # zh = auto()  # Simplified chinese

    @classmethod
    def names(cls) -> list[str]:
        return [e.name for e in cls]
    
@dataclass
class Options:
    # # True for generating block svg
    # # False for generating wall svg
    # block_mode: bool

    # Save constructed block images to "[block/wall]_sections/"
    debug_save_block_sections: bool

    # Workaround for wiki.gg flagging embedded fonts in @font-face as unsafe
    # Off by default
    embed_font_in_svg: bool

    language: Lang

    font_name: str = "Andy Std Bold"

    def get_font(self) -> str:
        return self.font_name + ".otf"

@dataclass
class AnimData:
    num_frames: int = 1
    frames_x: int = 1  # Number of frames in the x direction, if -1 assume frames go rightward forever
    frames_y: int = -1  # Number of frames in the y direction, if -1 assume frames go downward forever
    frame_offset: int = 0  # Start from for the animation
    frame_duration: int = 100   # Time per frame in miliseconds
    is_reversed: bool = False   # Does animation run backwards

type XIndex = int
type YIndex = int
type Lut = Sequence[Sequence[tuple[XIndex, YIndex]]]

@dataclass
class LutInfo:
    tiles_x: int  # X Tiles per frame
    tiles_y: int  # Y Tiles per frame
    pixels_from_border: int = 0  # Number of pixels from the edge to the first tile
    tile_space: int = SHEET_SCALE  # Number of pixels between tiles

@dataclass
class FrameInfo:
    info: LutInfo
    index_table: Lut

@unique
class ImageType(Enum):
    PNG = auto()
    GIF = auto()

@dataclass
class RenderedSection:
    image_type: ImageType
    data: bytes

@unique
class LayoutBehaviour(Enum):
    ALTERNATING = auto()
    CENTER = auto()

@dataclass
class LayoutOffsets:
    text_x_offset: float = TILE_SIZE * 4.5
    text_y_offset: float = TILE_SIZE + FONT_SIZE * 0.75
    row_advance: int = 2  # Space added between rows in a category
    category_advance: int = 2  # Space added between categories

# @dataclass
class Name:
    def __init__(self, **kwargs: str):
        """Provide names for each supported language code"""
        assigned = {l: False for l in Lang.names()}
        for lang, name in kwargs.items():
            setattr(self, lang, name)
            assigned[lang] = True

        if not all([b for b in assigned.values()]):
            raise TypeError(f"Missing names for {", ".join([l for l, b in assigned.items() if not b])}")

    def get(self, lang: Lang) -> str:
        return getattr(self, lang.name)

def fix_frame_dims(anim: AnimData) -> tuple[int, int]:
    # TODO fix janky indexing, what if both are -1?
    frames_x = anim.frames_x
    frames_y = anim.frames_y
    if frames_x == -1:
        frames_x = anim.num_frames
    if frames_y == -1:
        frames_y = anim.num_frames
    return frames_x, frames_y

class Metadata[BlockT, PatternT, CategoryT, ColumnLayoutT]:

    @staticmethod
    @abstractmethod
    def get_tile_dictionary() -> dict[CategoryT, Sequence[BlockT]]:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def get_template_and_lut(pattern: PatternT) -> FrameInfo:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def get_block_path(tile_number: int) -> str:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def image_folder_path() -> str:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def rendered_image_folder_path() -> str:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def get_tile_img_prepasses() -> dict[int, Callable[[Image.Image], None]]:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def render_block(img: Image.Image, block: BlockT, lut: FrameInfo, debug_save_block_sections: bool) -> RenderedSection:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def get_category_layout_info() -> Sequence[Sequence[ColumnLayoutT]]:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def get_layout_offsets() -> LayoutOffsets:
        raise NotImplementedError()