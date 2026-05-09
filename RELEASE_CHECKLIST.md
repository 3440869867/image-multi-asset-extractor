# Release Checklist

- [ ] Remove private files from `input_sheets/`.
- [ ] Remove generated PNGs from `output_png/`.
- [ ] Remove intermediate crops from `cropped/`.
- [ ] Remove manual review images from `review_needed/`.
- [ ] Remove generated JSON files from `manifest/`.
- [ ] Confirm `.venv/` is not staged.
- [ ] Run `python -m py_compile extract_assets.py app.py`.
- [ ] Run `python extract_assets.py --check-env`.
- [ ] Confirm README hardware notes are still accurate.
- [ ] Create a clean GitHub release tag.
