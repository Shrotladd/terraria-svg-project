
from PIL import Image
import numpy as np
import colorsys

from data import LutInfo


def extract_tile_animated_border(
        img: Image.Image, indices: tuple[int, int],
        num_frames_y: int, frame: int,
        tile_size: tuple[int, int], info: LutInfo,
        border_offsets: tuple[int, int, int, int] | None = None, 
    ) -> Image.Image:
    """
    Extract a tile out of a tile sheet, supports extracting frames of animation
    Args:
        img: Tile sheet
        indices: Which tile in the tile sheet to crop out, starts at the top left, note indices are not in pixels
        num_frames_x: How many frames are along the x direction, used for wrapping
        num_frames_y: How many frames are along the y direction, used for wrapping
        frame: Which frame in the tilesheet to choose from, starts from top left and descends
        tile_size: How large a tile is in pixels to crop out
        border_space: How many pixels there are between tiles
        border_offsets: How many pixels to include in left, up, right, down directions from the sides of a tile
    Returns:
        A subimage extracted from the tile
    """

    if border_offsets is None:
        border_offsets = (0, 0, 0, 0)
    
    x_px_stride = tile_size[0] + info.tile_space
    y_px_stride = tile_size[1] + info.tile_space

    x_offset = (frame // num_frames_y) * info.tiles_x * x_px_stride
    y_offset = (frame % num_frames_y) * info.tiles_y * y_px_stride

    x = indices[0] * x_px_stride + x_offset + info.pixels_from_border
    y = indices[1] * y_px_stride + y_offset + info.pixels_from_border

    return img.crop(
        box=(
            x + border_offsets[0],
            y + border_offsets[1],
            x + border_offsets[2] + tile_size[0],
            y + border_offsets[3] + tile_size[1],
        )
    )

def image_grid(images: list[Image.Image], horizontal_limit: int | None = None) -> Image.Image:
    """Takes a list of PIL images and stacks them horizontally to the specified limit then vertically.
    If tight is True, pack images as closely as possible, instead of minimising over lap
    """
    
    if horizontal_limit is None:
        horizontal_limit = np.iinfo(int).max
        
    n_horiz = min(len(images), horizontal_limit)
    h_sizes, v_sizes = [0] * n_horiz, [0] * (len(images) // n_horiz)
    
    for i, im in enumerate(images):
        h, v = i % n_horiz, i // n_horiz
        h_sizes[h] = max(h_sizes[h], im.size[0])
        v_sizes[v] = max(v_sizes[v], im.size[1])
        
    h_sizes, v_sizes = np.cumsum([0] + h_sizes), np.cumsum([0] + v_sizes)
    img_grid = Image.new('RGBA', (h_sizes[-1], v_sizes[-1]), color=(0, 0, 0, 0))
    
    for i, img in enumerate(images):
        img_grid.paste(img, (h_sizes[i % n_horiz], v_sizes[i // n_horiz]))

    return img_grid

def image_hue_shift(image: Image.Image, shift_by: float = 0.1, brightness: float = 1):
    def shift_hue(arr, hout):
        rgb_to_hsv = np.vectorize(colorsys.rgb_to_hsv)
        hsv_to_rgb = np.vectorize(colorsys.hsv_to_rgb)

        r, g, b, a = np.rollaxis(arr, axis=-1)
        h, s, v = rgb_to_hsv(r, g, b)
        h = hout
        r, g, b = hsv_to_rgb(h, s, v)
        arr = np.dstack((r, g, b, a))
        return arr
    img = image.convert('RGBA')
    pixels = img.load()
    assert(pixels is not None)
    for j in range(img.size[1]):
        for i in range(img.size[0]):
            pixels[(j, i)] = (int(pixels[(j, i)][0] * brightness), 0, 0, pixels[(j, i)][3]) # type: ignore
    pil_array = np.asarray(img).astype('float32')
    shifted_array = shift_hue(pil_array, shift_by).astype('uint8')
    new_img = Image.fromarray(shifted_array, 'RGBA')
    return new_img

def alpha_blend_img(source1_img: Image.Image, source2_img: Image.Image, mask: Image.Image) -> Image.Image:
    """Blend source1 and source2 with mask. Source images should be PIL images or a compatible type."""
    mask_arr = np.asarray(mask).astype('float32')
    mask_arr /= 255
    frame_arr = np.asarray(source1_img).astype('float32')
    shift_arr = np.asarray(source2_img).astype('float32')

    result_arr = (frame_arr * np.subtract(1, mask_arr)) + (shift_arr * mask_arr)
    return Image.fromarray(result_arr.astype('uint8'), 'RGBA')