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

# True for generating block svg
# False for generating wall svg
BLOCK_MODE: bool # Value assigned after argument parsing
# Save constructed block images to "[block/wall]_sections/"
DEBUG_SAVE_BLOCK_SECTIONS: bool # Value assigned after argument parsing

TERRARIA_FONT_NAME = "Andy Std Bold"
TERRARIA_FONT = TERRARIA_FONT_NAME + ".otf"

# Dimensions in # of tiles
SHEET_TILES_X = 16
SHEET_TILES_Y = 15
SHEET_SCALE = 2
FONT_SIZE = 20

# Space between top left corner of tiles, should be greater than the tile size.
TILE_SPACE = SHEET_SCALE * 9
TILE_SIZE = SHEET_SCALE * 8

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
    index: int
    image_type: ImageType
    data: bytes

@unique
class LayoutBehaviour(Enum):
    ALTERNATING = auto()
    CENTER = auto()

@dataclass
class LayoutOffsets:
    text_x_offset: float = TILE_SIZE * 4.5
    text_y_offset: float = TILE_SIZE + FONT_SIZE / 2
    row_advance: int = 2  # Space added between rows in a category
    category_advance: int = 2  # Space added between categories

def fix_frame_dims(anim: AnimData) -> tuple[int, int]:
    # TODO fix janky indexing, what if both are -1?
    frames_x = anim.frames_x
    frames_y = anim.frames_y
    if frames_x == -1:
        frames_x = anim.num_frames
    if frames_y == -1:
        frames_y = anim.num_frames
    return frames_x, frames_y

class Metadata[BlockT, PatternT, CategoryT, ColumnInfoT](Protocol):

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
    def render_block(img: Image.Image, block: BlockT, lut: FrameInfo) -> RenderedSection:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def get_category_layout_info() -> Sequence[ColumnInfoT]:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def get_layout_offsets() -> LayoutOffsets:
        raise NotImplementedError()