---
name: holo-card-studio
description: Create collectible holographic foil cards and two-image lenticular flip cards with AI-generated full-color ukiyo-e and colored sumi-e anime artwork, layered Blender scenes, renders, GLB export, and a flat white web viewer. Add optional local webcam gesture control to finished holographic cards. Use for 镭射卡、闪卡、全息卡、光栅卡、一念神魔、双形态卡、角色收藏卡、手势赏卡，或需要保持角色高度一致的 A/B 状态切换。
---

# Holo Card Studio

Create a finished collectible card project. The skill has two production routes that share one art direction and one delivery standard.

For an existing card that only needs gesture interaction, go directly to
[references/gesture-control.md](references/gesture-control.md). Reuse its finished
images and GLB; image generation and Blender rebuilding are unnecessary.

## Route first

Choose exactly one route before preparing assets:

- **Holographic foil** is the default route for one character artwork. It uses separate `subject`, `background`, `lineart`, and `text` planes, plus foil and sparkle effects.
- **Two-image lenticular** is the route for `光栅`, `翻转`, `双图`, `双形态`, or `一念神魔`. It uses two complete card artworks, A and B, and changes the whole card with viewing angle. Do not split one picture into left/right halves and do not fake the two states with SVG.

If the user asks for 一念神魔, route to lenticular automatically.

## Default art direction

Read [references/art-direction.md](references/art-direction.md) before generating art. Unless the user supplies another style, every generated card uses full-color Japanese ukiyo-e composition with colored sumi-e anime linework: expressive thick-to-thin ink contours, mineral pigments, visible brush texture, dramatic movement, and a coherent illustrated environment.

For a two-state card, generate A first, then edit A into B with the image-generation tool. Repeat the identity and composition invariants in the edit prompt. Keep the same face structure, hair/fur, costume anchors, proportions, camera, crop, body scale, and major silhouette. Expressions must clearly communicate the state: the benevolent state is serene, compassionate, and resolute; the malevolent state has focused predatory eyes, sharper brows, and a controlled feral or cruel expression without changing identity.

Foil and diamond sparkle are presentation layers, not substitutes for artwork. Default `foil` and `particles` to `1.0`; keep the face readable and preserve the ink contours.

## Generate images

Use the built-in image-generation tool for raster artwork. Do not ask the user to generate the images elsewhere. Do not use SVG or procedural stand-ins when a final illustration is requested.

For no-reference generation:

1. Generate the complete A artwork from the character brief using the default style.
2. Generate B by editing A. Lock identity, framing, and major geometry; change the expression, state-specific costume details, lighting, atmosphere, and action effects.
3. Save both as portrait PNG files with identical dimensions.

For reference-driven generation, treat the reference as the identity source and A as the direct adaptation. Then edit A into B. Read [references/lenticular-route.md](references/lenticular-route.md) for the required prompt structure and alignment checks.

## Build the project

Create a user-owned project directory outside this skill. Copy the matching example config and prepare its assets.

Holographic assets:

```text
assets/subject.png
assets/background.png
assets/lineart.png
assets/text.png
card-config.json
```

Lenticular assets:

```text
assets/image_a.png
assets/image_b.png
assets/text.png
card-config.json
```

Run the shared dispatcher:

```powershell
python scripts/run_pipeline.py --project <project-dir> --mode holographic
python scripts/run_pipeline.py --project <project-dir> --mode lenticular
```

`--mode` may be omitted when `card-config.json` contains `"mode"`. The default is `holographic`.

For lenticular projects, run `scripts/lenticular/prepare_pair.py` before the pipeline when normalization or an alignment report is needed. The pipeline creates typography when `text.png` is absent, validates assets, builds `card.blend`, renders previews, exports `web/assets/card.glb`, copies the matching web viewer, and installs its local web dependencies unless `--skip-npm` is supplied.

## Optional gesture presentation

When the user asks for 手势赏卡、隔空控制、双手缩放 or 响指转卡, read
[references/gesture-control.md](references/gesture-control.md) after the
holographic web export is ready. Run `python scripts/add_gestures.py --project
<project-dir>` to create a separate `web-gesture/` viewer. Keep the original
viewer intact. The first version supports the holographic route; do not silently
convert a lenticular card or promise untested gesture mappings.

Deliver whole-card zoom, enlarge-to-front, and an experimental visual snap that
toggles rotation, with explicit camera enable/stop and pointer/button fallback.
Verify the generated page in a browser and record real-user feedback separately
from synthetic gesture tests. Keep the camera off until the user enables it.

## Verify and deliver

Read [references/verification.md](references/verification.md). At minimum verify:

- the Blender scene contains physical card depth and multiple effect planes;
- A and B replace the entire illustrated face and remain recognizable as one character;
- front and angled renders show a readable state change;
- foil, glitter, line glow, and lenticular ridges are visible without washing out the face;
- the white web viewer loads the GLB and supports pointer/touch tilt without horizontal overflow.

Deliver the source images, `card.blend`, renders, web viewer, and a validation report. Keep generated binaries in the project, never inside the reusable skill archive.

## References

- [references/art-direction.md](references/art-direction.md): shared default style and prompt recipes.
- [references/holographic-route.md](references/holographic-route.md): multilayer foil-card workflow.
- [references/lenticular-route.md](references/lenticular-route.md): full-image A/B workflow and identity lock.
- [references/config.holographic.example.json](references/config.holographic.example.json): single-art config.
- [references/config.lenticular.example.json](references/config.lenticular.example.json): two-state config.
- [references/lenticular-model.md](references/lenticular-model.md): view-angle model.
- [references/verification.md](references/verification.md): render and browser acceptance checks.

