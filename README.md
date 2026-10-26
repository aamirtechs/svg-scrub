# svg-scrub

[![GitHub stars](https://img.shields.io/github/stars/aamirtechs/svg-scrub?style=social)](https://github.com/aamirtechs/svg-scrub/stargazers) [![GitHub forks](https://img.shields.io/github/forks/aamirtechs/svg-scrub?style=social)](https://github.com/aamirtechs/svg-scrub/network/members) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/aamirtechs/svg-scrub/blob/main/LICENSE) [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/aamirtechs/svg-scrub/issues)

Sanitize SVG files pasted from the web and prove the result is clean.
SVG files from icon sites, stock libraries and design tools often carry
scripts, event handlers, foreignObject embeds, external images and
tracking references; browsers and design tools run that content.
svg-scrub removes the dangerous parts locally, keeps every safe drawing
element and attribute, and reports a diff: exactly what was removed, per
category.

Zero dependencies. Python 3.9+.

## Why

Before dropping an SVG into a site, a slide deck or a design file, you
want one answer: is anything active or tracking still inside it?
svg-scrub gives that answer for a single file or a whole folder, works
offline, and never uploads anything. It also doubles as a CI gate:
`--check` exits nonzero when dangerous content is present, so a
publish pipeline can refuse to ship dirty SVGs.

## Install

```bash
pip install svg-scrub
# or just run the single file, it has no dependencies:
python3 svg_scrub.py --help
```

## Quick example

Generate the synthetic samples (they contain fake dangerous content
only, no real scripts or trackers), then check and clean them:

```bash
$ python3 examples/make_samples.py
wrote dirty.svg, tracker.svg, clean.svg

$ python3 svg_scrub.py --check examples/dirty.svg examples/tracker.svg examples/clean.svg
examples/dirty.svg: comment x1, event_handler x1, foreignobject x1, image x1, metadata x1, script x1, style_url x1, unsafe_link x1 [dangerous content found]
examples/tracker.svg: comment x1, image x1, metadata x1, processing_instruction x1, style_url x1, unsafe_link x1 [dangerous content found]
examples/clean.svg: clean
done: 3 file(s), 2 with dangerous content, 14 item(s) removed

$ python3 svg_scrub.py examples/dirty.svg examples/tracker.svg --out-dir cleaned/
examples/dirty.svg -> cleaned/dirty.clean.svg [removed comment x1, event_handler x1, foreignobject x1, image x1, metadata x1, script x1, style_url x1, unsafe_link x1]
examples/tracker.svg -> cleaned/tracker.clean.svg [removed comment x1, image x1, metadata x1, processing_instruction x1, style_url x1, unsafe_link x1]
done: 2 file(s), 2 with dangerous content, 14 item(s) removed

$ python3 svg_scrub.py --check cleaned/dirty.clean.svg cleaned/tracker.clean.svg
cleaned/dirty.clean.svg: clean
cleaned/tracker.clean.svg: clean
done: 2 file(s), 0 with dangerous content, 0 item(s) removed
```

(All outputs above are captured from real runs on the synthetic samples
in `examples/`.)

## What gets stripped

| Category | Removed |
| --- | --- |
| `script` | `<script>` elements |
| `foreignobject` | `<foreignObject>` elements (embedded HTML) |
| `handler` | `<handler>` elements |
| `metadata` | `<metadata>` elements |
| `comment` | XML comments, including prolog comments |
| `processing_instruction` | processing instructions, including prolog PIs |
| `doctype` | the DOCTYPE declaration |
| `event_handler` | `on*` attributes (`onclick`, `onload`, ...) |
| `unsafe_link` | `javascript:`, `vbscript:` and `data:text/html` links, and external `<use>` references |
| `image` | `<image>` elements whose href is not a safe raster data URI (external URLs, relative paths, `data:image/svg+xml`) |
| `style_url` | style attributes and `<style>` blocks referencing external URLs, `expression()` or `@import` |
| `editor` | inkscape/sodipodi elements and attributes, only with `--strip-editor` |

Kept by default: `title` and `desc` (accessibility), all safe drawing
elements and attributes, `http(s)` links on `<a>`, and raster data URI
images (`data:image/png`, `jpeg`, `gif`, `webp`). Safe content is never
re-encoded: drawing elements pass through the parser unchanged apart
from XML serialization, so cleaning cannot change how the picture looks.

## Flags

| Flag | Meaning |
| --- | --- |
| `--dir DIR` | clean a folder recursively (svg files, repeatable) |
| `--out-dir DIR` | write cleaned copies here instead of next to the inputs |
| `--suffix S` | suffix for cleaned copies (default: `.clean`) |
| `--in-place` | overwrite the input files |
| `--strip-editor` | also strip inkscape/sodipodi elements and attributes |
| `--check` | report only, exit 1 if any file has dangerous content |
| `--dry-run` | show what would be removed, write nothing |
| `--json` | print the full report as JSON |
| `--report PATH` | write the full report as JSON to a file |

## Limitations

- Serialization goes through `xml.etree`, so formatting is normalized
  (attribute quoting, self-closing tags, namespace prefixes for
  uncommon namespaces). Element and attribute content is preserved.
- The tool cannot see danger hidden in other encodings: base64 inside
  a kept raster data URI, or a `values` attribute on `<animate>` that
  rewrites a link at runtime. Those are listed in the good first issues.
- SVGs that rely on external resources (linked images, fonts, sprites)
  will lose those references by design; that is the point of a
  sanitizer, but check the diff report before shipping.

## Development

```bash
python3 -m pytest tests/ -q
```

## License

MIT. See LICENSE.
