# Verify a generated card

Keep generated images, logs, `.blend` files, and GLBs in the user's project,
outside the reusable skill. Check the requested route rather than assuming that
a successful run of one route validates the other.

## Pipeline and assets

1. Run `python scripts/run_pipeline.py --project <project-dir>`. An explicit
   `--mode` overrides the config's `mode`; a config without `mode` defaults to
   `holographic`. `--blender`, `--skip-render`, and `--skip-npm` reach the selected
   child pipeline. Malformed configuration and failed child processes must fail
   the command rather than reporting completion.
2. Confirm the route's expected PNGs share the same dimensions. Holographic
   subject and text require genuine transparent alpha; lineart requires dark
   contours on white. Review the artwork, typography, and registration visually.
3. Verify newly generated `card.blend`, `web/assets/card.glb`, the viewer config,
   and all referenced images. Old files left by a previous run do not prove that
   the current build succeeded. Check the Blender log and `verification.json`.
4. Both pipelines keep Blender preferences in `<project>/tools/blender-config`.
   Confirm the reported config directory when using an installed Blender.

## Blender

Open or render the saved scene and confirm that its images are packed and the
card has thickness. In the holographic route, foreground and background are
composited in the front material, typography uses a separate plane, and the
background reference plane is hidden in the render. Check the parallax controls
and at least a front and tilted view. Keep the face and text readable.

The holographic compositor supports the legacy scene-node API and the newer
scene compositor-group API; Glare settings also adapt to properties or sockets.
macOS selects Metal when available, with CPU fallback. Validate the Blender
version actually used; source compatibility branches are not a substitute for
testing every release or platform. Lenticular Blender-version compatibility
must be checked separately, including its effect-mask preparation stage.

For lenticular work, inspect the complete A/B state change and character identity
at both angles, along with ridges, foil, and particles. Do not substitute a
left/right split or a single unchanged picture.

## Browser

Start `node web/server.mjs` and open the printed localhost URL in a real browser.
Confirm the GLB and textures load, then test dragging, flip/return, auto rotation,
the available sliders, and image saving. On the holographic back, verify the
collection name and edition read normally instead of appearing mirrored.

Check a narrow viewport for horizontal overflow and cropped controls; test touch
on an actual touch device when claiming touch-device verification. Check the
browser console for application errors. Web shaders reproduce the effect rather
than Blender's exact lighting, so compare readability, parallax, and shimmer
without claiming identical pixels or identical back artwork.

## Focused source checks

For optional webcam control, follow [gesture-control.md](gesture-control.md).
Run the add-on installer against an existing holographic card and inspect its
separate viewer. Report synthetic gesture checks, real model execution, and
human camera feedback as different evidence. Do not rerun image generation or
Blender simply to add this presentation extension.

Run `python -m unittest discover -s tests -v` in a Python environment with Pillow.
These checks cover mode selection, argument forwarding, invalid configuration,
and stopping after a failed build even when stale outputs exist. They do not
replace rendering and browser inspection.
