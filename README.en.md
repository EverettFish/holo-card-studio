# 🃏 Holo Card Studio

Credit for the original technique: Xiaohongshu @乌托邦的香蕉🍌 (thanks for the tutorial!)

> A **Codex Skill**: say one sentence to Codex, get back a 3D holographic card that shimmers as you turn it.
> Drag it around in the browser, flip it to the back, pull the slider and watch it flare. Comes with an editable Blender project too.

The kind of foil card you couldn't afford at the stationery shop as a kid. Now you can print whoever you want on it.

---

## ✨ Thirty seconds

```
You: "Make me a cyberpunk mecha-cat holo card, neon rainy night background, No.007"

Codex:
  🎨 Paints four layers (subject / background / lineart / text)
  🧊 Builds the Blender scene: parallax, laser sheen, sparkle, all in place
  🌐 Assembles a Three.js page and serves it locally
  📦 Hands you: web link + card.blend + rendered stills
```

You do the imagining. It does the rest.

---

## 🎬 What you can make with it

### 🐱 A "legendary" card for your pet
Upload a photo of your cat, add "legendary rarity, gold border, name is Pudding".
The subject layer keeps her real expression and composition; background and lineart are painted fresh. Give it a drag: the cat pops forward, the background sinks back, rainbow foil flows with the angle. Post away.

### 🎮 Character cards for an indie game
One line per character, a full set in one go: warrior, mage, rogue, boss.
Every card ships with its own `card-config.json` holding rarity, number, and stat text. Edit it, rerun the pipeline, done. Drop a "pack opening" teaser before launch and watch players lose it.

### 🏢 Team anniversary or new-hire cards
Turn colleagues into cards: headshot as the subject, department color as the background, slogan as the text layer.
One card each, send the link, everyone spends an afternoon flipping their own. A hundred times more fun than a "meet the team" slide.

### 🎁 Valentine's, birthdays, anniversaries
"Retro film look, pink and gold, one line on the back."
Send a link, they turn it around on their phone, flip it, and find the message. Ceremony is mostly a matter of turning the shimmer up.

### 🎤 Easter egg material for talks and launches
Make a card for the product, then drop a link on your last slide: "scan this, it's the shiny kind."
The viewer is responsive, so it works in portrait or landscape, and the room starts spinning it on the spot.

### 🖌️ A material playground for designers
It isn't just a web page. `card.blend` is a genuinely editable Blender project.
The shared node group exposes `缩放` (scale), `深度` (depth), and `视差效果` (parallax) by name, with laser stripes, sparkle, and lineart glow as separate adjustable shader nodes. If you want to understand how a holo card actually shimmers, opening this file is the best textbook there is.

---

## 🧱 How a card is stacked

Four layers share one canvas, and parallax pushes them apart in space:

```
        👀 your eye
         │
   ┌─────┴──────┐
   │  text.png  │  text        ─ sits flat on the surface
   ├────────────┤
   │ lineart.png│  lineart     ─ glowing contours
   ├────────────┤
   │ subject.png│  subject     ─ pops toward you
   ├────────────┤
   │ background │  background  ─ recedes behind
   └────────────┘
```

On top of that: laser rainbow (phase follows your viewing angle, so it flares wherever you turn), Voronoi sparkle, gold card edge.
The browser rebuilds the four-layer composite with the same UV math via Three.js, reproducing the parallax and foil effect. Web shading and Blender's offline lighting differ, so colors, glow, and back artwork are not identical.

---

## 🚀 Usage

### Install
Drop this directory into your Codex skills folder:

```
~/.codex/skills/holo-card-studio/
```

### Requirements
- Python 3 + Pillow
- Node.js + npm
- Blender: **no manual install needed**. The pipeline pulls the official portable build into `<project>/tools/`, verifies the SHA-256, and keeps it project-local so nothing conflicts.

An installed Blender is reused first; use `--blender` to select an executable.
The holographic route handles both legacy compositor nodes and newer compositor
groups, and can use Metal on macOS. Preferences stay in the project's
`tools/blender-config/` directory.

Once the assets and config are ready, run:

```sh
python scripts/run_pipeline.py --project <project-dir> --mode holographic
```

Without `--mode`, the dispatcher reads the config's `mode`, falling back to
`holographic` when that field is absent. `--skip-render` skips still rendering;
`--skip-npm` skips web dependency installation. See the
[verification guide](references/verification.md) for runtime, render, and browser checks.

### Just ask
Then talk to Codex in plain language:

> "Use holo-card-studio to make me an ink-wash koi holo card, calligraphic text, No.001"

Or hand it a reference image:

> "Make a card from this image, keep the character and composition, swap the background for a starfield"

Codex will read back the card spec and everything it inferred, then get to work: paint the art → generate the text layer → write the config → run the pipeline → start a local server → actually open the page and test drag, flip, slider, and mobile layout → deliver.

### What you get back
| Thing | What it's for |
|---|---|
| Local web link | Drag, spin, flip, pull the slider |
| `card.blend` | Keep tuning materials, relight, render in Blender |
| `assets/` four layers | Swap any layer, rerun the pipeline |
| `card-config.json` | Change the name, number, rarity |
| Rendered stills | Ready to post |

---

## 🔧 Knobs you can turn

The pipeline ships with sensible defaults, and leaves every one of them open:

- **Parallax strength**: subject defaults to scale 1.25 / depth 0.4, background depth -0.25. Push it higher for more pop.
- **Laser stripes**: stripe density, distortion, angle, plus the pink → yellow → blue → white gradient
- **Lineart glow**: intensity and mask density, anywhere from a faint outline to full neon
- **Sparkle**: Voronoi scale + animated noise, from a few specks to a whole sky
- **Blender UI language**: Simplified Chinese by default, stored in the project-local config, switchable with one sentence

---

## 📁 Directory

```
holo-card-studio/
├── SKILL.md                    # The manual Codex reads
├── references/
│   ├── art-direction.md        # Prompt patterns for layered art, reference image handling
│   ├── config.example.json     # Sample card config
│   └── verification.md         # Pre-delivery checklist
├── scripts/
│   ├── ensure_blender.py       # Fetches the official portable Blender
│   ├── build_card.py           # Builds the editable Blender scene
│   ├── export_web.py           # Exports card geometry
│   ├── generate_typography.py  # Pixel-accurate transparent text layer
│   ├── validate_assets.py      # Health check on the four layers
│   ├── run_pipeline.py         # One-command pipeline
│   └── package_skill.py        # Packs the plain text into a shareable ZIP
└── assets/
    └── web-template/           # Responsive Three.js viewer
```

The skill itself is only code and text, so it stays light. Your generated art, `.blend` files, and models all live in your own output project.

---

## 🤝 Sharing the skill

Want to send it to a friend or drop it in a repo?

```bash
python scripts/package_skill.py
```

It packs text files only, by whitelist. The resulting ZIP is clean and ready to hand over.

## 🔀 New: two-image lenticular cards

Alongside the original single-art holographic route, the skill can now build lenticular flip cards, dual-state cards, and benevolent-versus-malevolent transformations.

This route uses two **complete card artworks**. The whole image changes from A to B with viewing angle; it does not split one picture into left and right halves. Without a reference, the default is full-color Japanese ukiyo-e composition with colored sumi-e anime linework. With a reference, the workflow generates A first and edits A into B while locking facial structure, proportions, costume anchors, framing, and subject scale.

The Blender file contains a physical card base plus separate image, lenticular ridge, holographic foil, line glow, and diamond-particle layers. The web viewer loads the GLB exported from Blender and drives the same full-card view-angle transition with mouse and touch tilt.

~~~bash
python scripts/run_pipeline.py --project <project-dir> --mode lenticular
~~~

A lenticular project uses:

~~~text
assets/image_a.png
assets/image_b.png
assets/text.png
card-config.json
~~~

The pipeline delivers card.blend, front/angled renders, web/assets/card.glb, the flat white Three.js viewer, and a validation report. The original holographic route remains available with --mode holographic; mode in card-config.json can select either route automatically.

---

*So, who's on your first card?* ✨

## Optional webcam gesture control

Add a separate gesture viewer to a finished holographic card:

```bash
python scripts/add_gestures.py --project <finished-card-project>
cd <finished-card-project>/web-gesture
npm start
```

Spread both hands to enlarge the whole card and return to its front, bring them
together to shrink, or touch and quickly release the thumb and middle finger to
toggle continuous rotation after the ready cue. The visual snap is experimental;
keep the existing pointer, keyboard, and button controls available.

The original card assets and viewer stay intact. Camera access is off by default
and explicitly enabled by the user. Processing is local, with no microphone,
recording, or upload. The model is downloaded and hash-checked during project
setup, not distributed inside the text-only skill. Holographic cards are supported;
lenticular integration is not included. See [setup, tuning, and real-use checks](references/gesture-control.md).
