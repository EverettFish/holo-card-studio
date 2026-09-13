# Optional gesture presentation

Use this extension when a user wants to control a holographic card with their
hands, or to add gesture interaction to an existing card. The artwork and its
interaction should feel like one finished experience. Reuse the card's images,
GLB, title, and material settings; preserve its requested art direction.

This first version uses the canonical **holographic** GLB material roles and
four PNG layers. The lenticular viewer has a different scene and is not supported
by this installer. Custom viewer code is not migrated: the extension creates a
separate viewer using the skill's gesture template.

## Attach it to a finished card

The input is a completed project containing `web/card-config.json` and the five
local assets referenced by its `assets` object: `subject`, `background`,
`lineart`, `text`, and `model`. The first four must be PNGs; `model` must be a GLB.
Finish the ordinary holographic pipeline first when these exports do not exist.

From the skill directory:

```bash
python scripts/add_gestures.py --project <finished-card-project>
```

The command creates `<finished-card-project>/web-gesture/`. It copies only the
needed card assets, checks their SHA-256 hashes, and writes a browser config and
`gesture-assets.json`. The original `web/`, artwork, and Blender project remain
unchanged. Existing output directories are rejected; use `--out <new-directory>`
to create another copy. Output must be outside both the original viewer and the
skill. Remote assets and paths escaping the source `web/` are rejected.

Python 3.9+, Node.js 18+, and npm are required. The default command installs the
locked browser dependencies with `npm ci` and downloads the fixed Google hand
model (7,819,105 bytes), verifying the SHA-256 recorded in
`assets/web-gesture/models/manifest.json`. Model weights, WASM, npm dependencies,
generated images, and GLBs are never part of the reusable skill archive.

To stage files without installing dependencies or downloading a model, use
`--skip-npm --skip-model`. Finish setup from the generated viewer directory:

```bash
npm ci
npm run setup:model
npm start
```

Open the printed `http://127.0.0.1:4186/` URL in Chrome. `PORT` selects another
available port. The server binds to localhost and reports a conflict rather than
reusing an unknown service. Directly opening `index.html` does not work. Dependencies
and the model load from the local server after setup; camera frames are processed
only in the browser and its Worker. There is no microphone, recording, or upload.

## Interaction to deliver

| Action | Result |
| --- | --- |
| Enable gesture control | Load the local model, then ask for camera access |
| Hold both hands in view briefly | Calibrate current hand distance against current card size |
| Spread hands | Enlarge the whole card and return to its original front angle |
| Bring hands together | Shrink the whole card while keeping its orientation |
| Thumb and middle finger touch, then quickly release after “ready” | Toggle continuous 360° rotation; experimental visual snap |
| Pause rotation | Keep the current angle; the next enlargement returns to the front |
| Lose a hand or leave the frame | Freeze the visible size and rebase after stable reacquisition |
| Use mouse, keyboard, or a card button | Give manual interaction priority and rebase the hand distance |
| Stop control, hide the tab, or leave the page | Release camera/Worker resources; no automatic camera restart |

Whole-card zoom changes the camera projection. The existing **subject scale**
slider changes the artwork material and remains independent. Defaults are
70–118% zoom, 250 ms calibration, a 2.5% distance dead zone, and smoothed updates.

The snap candidate requires two contact observations, at least 35 ms contact,
and a rapid middle-finger release within 220 ms. Wait at least 1.2 seconds
between actions. Show the existing contact/ready/cooldown cues; a static pose
must not trigger rotation. After a snap, hold scale for 450 ms and rebase so
incidental palm movement does not immediately cancel the spin by enlarging.
Ordinary index pinches, slow releases, tracking loss, and single-frame contact
have negative tests. Pure visual detection can still miss real snaps or mistake
similar movements; keep the rotation button available.

## Reuse and adjustment

`assets/web-gesture/` is an optional viewer template, parallel to the existing
holographic and lenticular templates. Its renderer is adapted from the
holographic viewer and uses the same front/back shaders. Gesture changes are
contained here so the default viewers do not acquire a camera dependency.
When upstream changes material or GLB conventions, review this template too.

The generated viewer contains:

- `gestures/gesture-engine.js`: camera-independent gesture state and thresholds
  (`SETTINGS`), palm-size normalization, identity matching, calibration, and cooldown.
- `gestures/card-motion.js`: zoom interpolation, original-front orientation, and
  12-second continuous rotation. Defaults match the canonical holographic viewer.
- `gestures/camera-session.js` and `hand-worker.js`: resource lifecycle and one
  inference frame at a time, capped at approximately 24 fps.
- `gestures/gesture-ui.js`: visible readiness feedback and manual-operation priority.

Tune thresholds against actual use of the generated card. Keep changes local to
that project unless the user asks to update the skill. Do not compensate for slow
inference by queueing frames: the current Worker path drops excess work. Rendering
uses a lower pixel-ratio cap while gesture control is active; this reduces drawing
load but does not establish that a particular device's stutter is solved.

## Verify the extension

From the skill directory, run the focused source checks:

```bash
python -m unittest discover -s tests -p 'test_add_gestures.py' -v
node --test tests/gestures/*.test.mjs
```

Then **actually run the installer on a finished card**, ideally from an unpacked
skill archive, and start that generated viewer. Confirm it shows the source
card's title, artwork, and material settings. Check the copied asset hashes;
source files must not change.

Open `/check.html` on that viewer and run its controlled browser checks. These
exercise the real scene, front/back rotation, pause/enlarge-to-front, independent
subject scale, and actual MediaPipe inference on generated blank video frames.
They do not request a camera and do not prove real-hand recognition. Use real
pointer interaction and inspect a narrow viewport as well.

For human trial, explicitly enable the camera and try stable entry, spreading,
bringing hands together, loss/re-entry, snap readiness, and a second snap after
cooldown. Ask whether enlargement returns to the original face and whether snaps
start/pause rotation reliably enough. Check stopping/backgrounding releases the
camera. Record device/browser, observed behavior, and remaining uncertainty.
Never present synthetic sequences, blank-frame model execution, or a qualitative
improvement as a measured real-world recognition rate.

Deliver the generated viewer path, startup command, source-check results,
browser results, and the human-trial status. Preserve the original card project.

## Implementation sources

- [Google Hand Landmarker for Web](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/web_js)
  documents video input and moving synchronous detection off the UI thread.
- [Google's Worker example](https://github.com/google-ai-edge/mediapipe-samples-web/blob/main/src/workers/hand-landmarker.worker.ts)
  demonstrates the independent inference path.
- The pinned model download URL and hash are in the template's model manifest;
  `@mediapipe/tasks-vision` is locked at `1.0.1` and Three.js at `0.180.0`.
