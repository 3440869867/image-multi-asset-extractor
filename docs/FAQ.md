# FAQ

## Why did my image go to `review_needed/`?

The detector could not find reliable asset boxes. Common causes:

- Elements are touching each other.
- Text labels overlap the asset.
- The background is too complex.
- Shadows are extremely faint.
- The whole page is surrounded by a thick decorative frame.

## Why are tiny labels ignored?

The tool filters likely text, index numbers, headers, and frames so the exported PNGs are actual map assets instead of sheet annotations.

## Can I use AMD GPU?

Best effort. Windows AMD users can try DirectML with `requirements-amd-directml.txt`.
Linux AMD users can try ROCm with `requirements-amd-rocm.txt`.
If those backends are not available, use CPU mode.

## Can I open source assets produced by this tool?

The tool can mark generated items as `commercialSafe`, but it cannot verify the legal status of source images. Only process assets that you have the right to use and redistribute.
