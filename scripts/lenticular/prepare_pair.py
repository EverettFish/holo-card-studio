"""Normalise two source images to one opaque canvas and score how well their compositions line up."""
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps
import argparse, json, math


def fit_canvas(im, size, mode):
    """Return an opaque RGB image at `size`. cover = centre crop; contain = pad with a blurred stretch."""
    im = ImageOps.exif_transpose(im)
    if im.mode in ('RGBA', 'LA', 'P'):
        base = Image.new('RGB', im.size, (18, 18, 22))
        base.paste(im.convert('RGBA'), mask=im.convert('RGBA').getchannel('A'))
        im = base
    im = im.convert('RGB')
    if mode == 'cover':
        return ImageOps.fit(im, size, Image.LANCZOS, centering=(0.5, 0.5))
    backdrop = ImageOps.fit(im, size, Image.LANCZOS).filter(ImageFilter.GaussianBlur(max(size) / 40))
    scale = min(size[0] / im.width, size[1] / im.height)
    inner = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
    backdrop.paste(inner, ((size[0] - inner.width) // 2, (size[1] - inner.height) // 2))
    return backdrop


def edge_map(im, size=(64, 96)):
    g = im.convert('L').resize(size, Image.LANCZOS).filter(ImageFilter.FIND_EDGES)
    px = list(g.tobytes())
    mean = sum(px) / len(px)
    return [p - mean for p in px]


def similarity(a, b):
    """Pearson correlation of low-resolution edge maps: 1 = identical layout, ~0 = unrelated."""
    ea, eb = edge_map(a), edge_map(b)
    num = sum(x * y for x, y in zip(ea, eb))
    den = math.sqrt(sum(x * x for x in ea) * sum(y * y for y in eb)) or 1
    return num / den


def prepare(project, a, b, width=None, height=None, fit='cover', swap=False):
    root = Path(project).resolve(); assets = root / 'assets'; assets.mkdir(parents=True, exist_ok=True)
    if swap: a, b = b, a
    with Image.open(a) as ia, Image.open(b) as ib:
        ia.load(); ib.load()
        if width and height: size = (width, height)
        else:
            w, h = ImageOps.exif_transpose(ia).size
            scale = min(1, 2048 / max(w, h)); size = (round(w * scale), round(h * scale))
        fa, fb = fit_canvas(ia, size, fit), fit_canvas(ib, size, fit)
    fa.save(assets / 'image_a.png'); fb.save(assets / 'image_b.png')
    score = similarity(fa, fb)
    diff = sum(abs(x - y) for x, y in zip(fa.resize((32, 48)).convert('L').tobytes(), fb.resize((32, 48)).convert('L').tobytes())) / (32 * 48 * 255)
    report = {'canvas': size, 'fit': fit, 'composition_similarity': round(score, 3), 'mean_difference': round(diff, 3),
              'verdict': ('frames look registered' if score >= 0.25 else 'strong state change; manually confirm face and anchors' if score >= 0.15 else 'B may have drifted: inspect identity and composition anchors')}
    if diff < 0.02: report['verdict'] = 'frames are nearly identical: the flip will be invisible'
    (root / 'pair-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('project'); p.add_argument('--a', required=True); p.add_argument('--b', required=True)
    p.add_argument('--width', type=int); p.add_argument('--height', type=int)
    p.add_argument('--fit', choices=['cover', 'contain'], default='cover'); p.add_argument('--swap', action='store_true')
    args = p.parse_args()
    print(json.dumps(prepare(args.project, args.a, args.b, args.width, args.height, args.fit, args.swap), ensure_ascii=False, indent=2))
