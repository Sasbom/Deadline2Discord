import OpenEXR as exr
import numpy as np
from PIL import Image
from pathlib import Path


def apply_sRGB(exrchannel):
    """Apply a sRGB gamma curve to numpy ndarray."""

    def linear_to_srgb(value):
        """Convert linear RGB to sRGB."""
        if value <= 0.0031308:
            return 12.92 * value
        else:
            return 1.055 * (value ** (1/2.4)) - 0.055
        
    correct_srgb = np.vectorize(linear_to_srgb)
    return correct_srgb(exrchannel.pixels)


def pil_image_fromEXRchannel(exrfile, channel:str):
    """Extract exr float channels and map them for
    unsigned char 8 bit png on sRGB gamma curve"""
    img_data = exrfile.channels()[channel]
    rgb_data = apply_sRGB(img_data)
    image_normalized = np.clip(rgb_data*255,0,255).astype(np.uint8)
    return Image.fromarray(image_normalized)


def comp_layers(exrfile, *channels):
    """Quick composite layers by pasting them on top of eachother"""
    layers = [pil_image_fromEXRchannel(exrfile,c) for c in channels]
    layer_it = iter(layers)
    image = next(layer_it)
    for l in layer_it:
        image.alpha_composite(l,(0,0))
    return image


def blender_get_combined_layers(exrfile):
    """Main format for renderlayers is 'Viewlayer.Combined.X' 
    so assume all combined layers are to be composited."""
    return [k for k in exrfile.channels().keys() if "Combined" in k]


def find_rgba_channel(exrfile):
    """Check RGBA or RGB layer. This is the usual suspect for a render."""
    channels = exrfile.channels()
    rgba = channels.get("RGBA", None)
    if rgba:
        return "RGBA"
    rgb = channels.get("RGB", None)
    return "RGB" if rgb else None


def convert_exr_to_png(path: str):
    path_img = Path(path)
    imagename = path_img.stem
    png_img = path_img.parent / f"{imagename}.png"
    with exr.File(path) as exrfile:
        regularchannel = find_rgba_channel(exrfile)
        image = None
        if regularchannel:
            # in case a regular RGB / RGBA channel is available, take that.
            image = pil_image_fromEXRchannel(exrfile, regularchannel)
        else:
            layers = blender_get_combined_layers(exrfile)
            if layers:  
                image = comp_layers(exrfile,*layers)
        if image:
            image.save(str(png_img))
            return png_img
    return None


# source_img = R"X:\_PROJECTS\ANI2_3D\project_TheSearch\04_Render\Shots\SET_2_SH_18\EXR\SH-18_V01_0061.exr"
# 
# 
# with exr.File(source_img) as exrfile:
#     complayers = blender_get_combined_layers(exrfile)
#     image = comp_layers(exrfile,*complayers)
#     image.save("output_test_comp.png")

# with exr.File(source_img) as exrfile:
#     img_data = exrfile.channels()["BG.Combined"]
#     correct_srgb = np.vectorize(linear_to_srgb)
#     rgb_data = correct_srgb(img_data.pixels)
#     image_normalized = np.clip(rgb_data*255,0,255).astype(np.uint8)
#     
#     out_image = Image.fromarray(image_normalized)
#     out_image.save("output_test.png")