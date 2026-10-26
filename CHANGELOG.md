# Changelog

## v1.0.0 (2026-10-26)

- Initial release: sanitize SVG files with a per-category diff report.
- Removes script, foreignObject and handler elements; metadata,
  comments, processing instructions and the DOCTYPE declaration.
- Removes on* event handlers, javascript:/data:text/html links,
  external image references (safe raster data URIs kept), dangerous
  style attributes and style blocks, and external use references.
- Keeps title and desc by default; --strip-editor also removes
  inkscape/sodipodi elements and attributes.
- --check CI gate, --dry-run, --dir batch mode, --in-place, --out-dir,
  --json and --report output.
- 20 tests, all passing.
