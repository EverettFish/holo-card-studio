---
name: holo-card-studio
description: Generate interactive 3D holographic collectible-card websites from a user description or reference image, using layered artwork, Blender and Three.js. Includes project-local Blender installation, reusable parallax materials and browser verification.
---

# Holo Card Studio

Turn the user's description or uploaded reference into a finished, editable Blender card and an interactive Three.js page. Preserve the requested subject, style, typography and destination. This skill contains code and text only; generated artwork belongs in the user's output project.

## Working sequence

1. Establish the output project and a compact card specification. Infer harmless missing design details and state them. Read [references/art-direction.md](references/art-direction.md) for layered image prompts and reference handling. Do not assume every card is anime, Japanese, or based on the example that inspired this skill.
2. Generate subject, background and registered line art with the available image-generation tool. For an uploaded reference, inspect it first and preserve the requested identity/composition. Use the built-in image tool when available; never silently substitute an API requiring a key or paid service. Save assets under the output project's `assets/` as `subject.png`, `background.png`, `lineart.png`. Create accurate transparent `text.png` with `scripts/generate_typography.py` or equivalent typography tooling. Never package those output assets into this skill.
3. Use [references/config.example.json](references/config.example.json) as the schema example; write the user's metadata to `<project>/card-config.json`. Generate all four layers on the same canvas. Run `scripts/validate_assets.py <project>` and visually inspect transparency and registration. A drawn checkerboard is not transparency. A newly generated line drawing may drift; compare it to the source and regenerate before allowing bright contours.
4. Run `scripts/run_pipeline.py --project <project>`. It locates Blender, installs an official portable copy into `<project>/tools` if absent, generates the editable scene, exports geometry from that scene, and assembles the Three.js website. Python with Pillow, Node.js and npm must be available. Inspect missing-dependency errors; do not claim completion or repeatedly retry the same blocker.
5. Start the local site with `node <project>/web/server.mjs`; keep the process alive and open its returned localhost URL. Read [references/verification.md](references/verification.md), then actually test rendering, dragging, flipping, slider effects and mobile layout. A ready flag alone does not prove shaders compiled or the scene looks right.
6. If requested, open `<project>/card.blend` in the installed Blender and verify a visible window with the requested UI language. Preserve a long-running process when short-lived launchers terminate child apps. The default requested locale is Simplified Chinese and is stored in Blender's project-local portable config. Re-read user intent if another locale is wanted.
7. Deliver the working URL, source project, editable `.blend`, and renders. State that custom Blender shader graphs are rebuilt in Three.js; glTF does not transfer this graph directly. Publish a website or repository only when that publication is requested. For a requested skill ZIP/repository, use `scripts/package_skill.py`; never include output projects, images, model binaries with embedded images, credentials, dependencies, or caches.

## Non-obvious invariants

- All image planes are created in XY with object rotation X=90 degrees. Keep that rotation unapplied. Editing the mesh to simulate the rotation breaks the intended local axes.
- Default core controls: subject scale 1.25, subject depth 0.4, background depth -0.25; text scale 1 and depth 0. The shared group has inputs `缩放` and `深度`, output `视差效果`. A fixed layout safety mapping can preserve room for text; keep it separate from the user's parallax controls.
- UV centering and normal transformation alone cannot create full view-dependent parallax. Also transform the viewing direction into the card plane, divide by a bounded normal component, and offset UV by signed depth.
- The face mixes background and subject BSDF with subject Alpha. Keep metallic=1 and roughness=1 where requested; avoid hiding a bad material under extreme emission.
- Foil uses mapped bands (scale about 0.55, distortion 7, mapping Y about 32 degrees), a separate pattern image mapping, Multiply/Add, pink-yellow-blue-white ramp and Overlay. The spectrum phase must change with viewing angle, not only time.
- Keep subject BSDF emission black; combine stripe emission and desaturated thresholded line emission separately. The line node may use strength 40 but must be sparsely masked to retain the printed character details. Stars combine Voronoi distance to edge and animated noise. Card sides use a separate material slot; compositor glow is high quality.
- Export real Blender card geometry, not a flat screenshot presented as an imported model. Use `web_front`, `web_edge`, `web_back`, `web_gold` material names as the browser contract. The Three.js page composites four image layers with matching UV formulas.
- Blender local axes change during glTF's Y-up conversion. In the supplied browser template, use the canonical card root frame for `uView`, not the converted front mesh's local frame; restore the exported V coordinate exactly once. Test both turn directions to catch smearing and inverted parallax.

## Resources

- `scripts/ensure_blender.py`: official-release discovery, SHA-256 validation and project-local extraction.
- `scripts/build_card.py`, `scripts/export_web.py`: editable Blender scene and geometry export.
- `assets/web-template/`: responsive Three.js viewer. No source artwork is included.
- `scripts/generate_typography.py`, `scripts/validate_assets.py`, `scripts/run_pipeline.py`: deterministic production helpers.
- `scripts/package_skill.py`: text-only allowlist, content checks and ZIP verification.
