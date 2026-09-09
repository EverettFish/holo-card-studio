# Two-image lenticular route

Use this route for 光栅、翻转、双形态、or 一念神魔 cards.

## Image pair

`image_a.png` and `image_b.png` are two complete edge-to-edge illustrations. Each image includes character, environment, lighting, particles, and painted foil cues. The pair is never a left/right split and never a background-only swap.

Generate A first. Generate B as an edit of A using the identity-preserve prompt in `art-direction.md`. Keep identical dimensions. Prefer the same head center, body scale, crop, and dominant diagonals. State-specific changes can cover expression, costume details, palette, atmosphere, and supernatural action.

## Pair preparation

Run:

```powershell
python scripts/lenticular/prepare_pair.py --image-a <A.png> --image-b <B.png> --project <project-dir>
```

Review the pair report. Low pixel similarity is acceptable when environments change, but facial identity and compositional anchors must match by inspection.

## Physical model

The Blender scene creates a card body, A/B image planes, a clear lenticular lens layer, line-glow planes, particle/diamond effects, and foil response. The web shader blends A and B from view angle. Read `lenticular-model.md` for the parameter definitions.

Use these defaults for a showcase build:

```json
{
  "flipAngle": 18,
  "softness": 0.22,
  "pitch": 120,
  "stripe": 0.22,
  "sweep": 4,
  "refract": 0.3,
  "ridge": 0.5,
  "depth": 0.03,
  "foil": 1.0,
  "particles": 1.0,
  "glow": 0.85
}
```
