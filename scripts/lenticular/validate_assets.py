"""Validate the two opaque frames and the transparent text layer before building."""
from pathlib import Path
from PIL import Image
import argparse, json


def validate(project):
    root = Path(project); report = {}; size = None
    for name in ['image_a', 'image_b', 'text']:
        file = root / 'assets' / (name + '.png')
        if not file.exists(): raise FileNotFoundError(str(file) + ' is missing')
        with Image.open(file) as im:
            if im.format != 'PNG': raise ValueError(str(file) + ' is not a PNG')
            if not size: size = im.size
            if im.size != size: raise ValueError('Layer dimensions differ: ' + name + ' ' + str(im.size) + ' vs ' + str(size))
            if min(im.size) < 256: raise ValueError('Artwork is too small: ' + name)
            item = {'size': im.size, 'mode': im.mode}
            if name == 'text':
                if 'A' not in im.getbands(): raise ValueError('text lacks real alpha')
                hist = im.getchannel('A').histogram(); total = sum(hist)
                transparent = sum(hist[:16]) / total; solid = sum(hist[128:]) / total
                if transparent < .3 or solid < .0005: raise ValueError('text needs a mostly transparent canvas with some visible glyphs')
                item.update(transparent_fraction=round(transparent, 4), visible_fraction=round(solid, 4))
            else:
                lo, hi = im.convert('L').getextrema()
                if hi - lo < 40: raise ValueError(name + ' is nearly flat; is it the right file?')
            report[name] = item
    with Image.open(root / 'assets' / 'image_a.png') as a, Image.open(root / 'assets' / 'image_b.png') as b:
        pa = a.convert('L').resize((32, 48)).tobytes(); pb = b.convert('L').resize((32, 48)).tobytes()
        diff = sum(abs(x - y) for x, y in zip(pa, pb)) / (32 * 48 * 255)
    if diff < 0.015: raise ValueError('image_a and image_b are nearly identical; a lenticular flip needs two different frames')
    report['pair_mean_difference'] = round(diff, 4)
    (root / 'asset-validation.json').write_text(json.dumps(report, indent=2), encoding='utf8'); return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('project'); a = p.parse_args(); print(json.dumps(validate(a.project), indent=2))
