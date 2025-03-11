from PIL import Image
from pathlib import Path

def optimize_image(image_path: Path, scale = 0.75, qual = 75):
    filename = image_path.stem
    suffix = image_path.suffix
    if suffix != ".png":
        return image_path
    new_path = image_path.parent / f"{filename}_opt.png"
    img = Image.open(image_path)
    w, h = img.size
    new_w, new_h = w*scale, h*scale
    img.resize((new_w,new_h))
    img.save(new_path,optimize=True,quality=qual)
    return new_path
    
