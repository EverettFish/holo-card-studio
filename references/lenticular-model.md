# Lenticular model shared by Blender and GLSL

Both renderers implement the same formulas so the browser matches the offline render. All vectors are in the **card-root frame**: X across the card, Y up the card, Z out of the front face. `V` is the unit vector from the shading point toward the camera. `u` is the raw horizontal UV in 0..1 (V of the texture is 1−uv.y after the glTF export).

## 1. Local viewing angle

```
angle = degrees(atan2(V.x, max(V.z, 0.05)))      // signed, per shading point
angle += (u − 0.5) · sweep                        // lens-pitch drift, sweep in degrees
```

Because `V` is computed per point under a perspective camera, `angle` already varies a few degrees across the face; `sweep` (default 6°) exaggerates it so the flip visibly travels from one edge to the other. Setting sweep to 0 gives a near-simultaneous switch.

## 2. Phase and image index

```
p     = |angle| / flipAngle                       // 0 = frontal, 1 = full flip
mono  = min(p, 1)                                 // default: stays on B once tilted
tri   = |mod(p + 1, 2) − 1|                       // cycle: A → B → A → B …
t     = mix(mono, tri, cycle)
```

`flipAngle` (default 14°) is the tilt where the centre of the card has fully switched; the midpoint of the transition therefore sits at half that angle. Both tilt directions switch to B, which keeps the resting card a clean frame A. The cyclic variant reproduces a real two-flip lenticular, where continuing to tilt brings A back.

## 3. Interlace and transition softness

```
lensC = fract(u · pitch) − 0.5                    // position inside one lenticule, −0.5..0.5
t    += lensC · stripe · 0.5                      // each strip switches at a slightly different angle
mix   = smoothstep(0.5 − soft, 0.5 + soft, t)
```

`pitch` (default 120 lenticules across the card) and `stripe` (default 0.35) control how much of the classic alternating-strip look shows inside the transition band; stripe 0 is perfectly smooth, 1 is a hard interlace. `soft` (default 0.22, range 0.05–0.5) widens the band from a crisp flip to a dreamy cross-fade. The stripes are pinned to the raw UV, never to a parallaxed UV.

## 4. Artwork lookup

```
uvArt   = (uv − 0.5) · 1.04 + 0.5 + V.xy / max(|V.z|, 0.35) · depth · 0.14
uvArt.x += lensC · refract / pitch
colour  = mix(texture(A, uvArt), texture(B, uvArt), mix)
```

`depth` (default 0.08) lets the print float a hair behind the lens; `refract` (default 0.3) is the cylindrical-lens magnification inside each lenticule that gives the fine shimmer. Both are small; the flip is the effect, these only add life.

## 5. Lens sheet finish

```
ridgeN = normalize(vec3(lensC · 2 · ridge, 0, 1))          // cylinder cross-section
spec   = pow(max(dot(ridgeN, normalize(V + L)), 0), 28)    // L ≈ normalize(0.35, 0.6, 1)
fres   = pow(1 − max(dot(ridgeN, V), 0), 4)
```

In Blender the same ridge is a Bump node with height `1 − 4·lensC²` connected only to the Principled BSDF **Coat Normal** (coat weight 1, coat roughness 0.12). The base normal stays flat so the print underneath is undistorted.

## 6. Foil and ghosting

Foil reuses angle-driven bands: `w = 0.5 + 0.5·sin((a.x·0.848 − a.y·0.530)·2π·0.55 + 7·noise(a·1.5))` with `a = uv + V.xy·2.4`, mapped through a pink→yellow→blue→white ramp and overlaid at `0.3 · foil`. A narrow angle-driven sweep adds emission. During the transition the artwork is darkened by `(1 − |2·mix − 1|) · 0.06`, the slight luminance dip a real lenticular shows when both frames are half visible.

## Parameter table (card-config.json `lenticular`)

| key | default | range | UI label |
| --- | --- | --- | --- |
| flipAngle | 14 | 6–30 | 翻转角度 |
| softness | 0.22 | 0.05–0.5 | 过渡柔和 |
| pitch | 120 | 40–240 | 光栅密度 |
| stripe | 0.35 | 0–1 | 条纹显现 |
| sweep | 6 | 0–20 | 扫掠 |
| refract | 0.3 | 0–2 | 柱镜折射 |
| ridge | 0.5 | 0–1.5 | 镜片光泽 |
| depth | 0.08 | 0–0.3 | 景深 |
| foil | 0.35 | 0–1 | 镭射强度 |
| cycle | false | bool | 真实循环 |
