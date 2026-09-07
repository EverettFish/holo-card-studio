# Finish by observing the result

- Validate real alpha (subject and text), equal canvas dimensions, nonempty artwork, and line-art contrast. Visually inspect exact names, anatomy, clipping, registration and text overlap.
- Inspect Blender: X=90 degrees remains an object transform on all three planes; packed assets and relative paths; correct parameters; edge material assignment; connected compositor glow. Render front and both tilt directions. Check normal and UV conventions before tuning foil when bands point in the wrong direction.
- Confirm the actual requested-language GUI if opening it was requested. A saved preference or an executable process alone does not prove the visible interface opened.
- Parse the exported GLB and confirm it contains meshes and the browser material-role names. The export is geometry plus simple role materials, not a raster render of the completed card.
- Run the site in an actual browser with WebGL. Fail on shader compilation errors or missing model/asset requests. Wait for textures and model before taking a screenshot. Test pointer drag, touch-sized layout, flip/back design, reset, auto motion, each parameter, screenshot download and keyboard controls. Check layout around 390px and desktop widths. Avoid desktop-width overflow and confirm the reduced-motion setting is respected.
- Browser image comparisons must demonstrate observable rotation and a change after foil adjustment; a boolean ready flag or source grep is insufficient. Test both signed-depth directions. In particular, using the exported front mesh frame rather than the canonical card root can turn local Y into the normal and smear UVs.
- glTF cannot preserve this custom Blender node graph. Explain that web materials reproduce the effect with GLSL; minor render differences are expected. Never advertise pixel-identical offline and real-time renders without proving them.
- For text-only distribution, run package_skill.py, inspect every archive member, scan for embedded image data and require UTF-8 text. Exclude assets generated for any individual card, including image-bearing .blend/.glb/.gltf and videos. A PNG encoded in JavaScript is still image content and must not be included.

The template exposes window.__holo.ready, root, uniforms and renderer for local testing. It does not grant access to any external service.
