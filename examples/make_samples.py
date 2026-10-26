#!/usr/bin/env python3
"""Generate small synthetic SVG samples with fake dangerous content.

The samples contain no real tracking or real scripts: every payload is
a harmless placeholder (example.com, alert("demo")) so the README
examples and the --check demo run anywhere. Run from the project root:

    python3 examples/make_samples.py
    python3 svg_scrub.py --check examples/
"""

from pathlib import Path

DIRTY = """<?xml version="1.0" encoding="UTF-8"?>
<!-- pasted from a random icon site -->
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="200" height="100" viewBox="0 0 200 100">
  <title>Demo icon</title>
  <desc>A circle and a link, as pasted from the web.</desc>
  <metadata>Author: demo, exported by Example Editor 1.0</metadata>
  <script>alert("demo")</script>
  <foreignObject width="100" height="50"><div>embedded html</div></foreignObject>
  <circle cx="50" cy="50" r="40" fill="steelblue" onclick="alert('demo')"/>
  <a xlink:href="javascript:alert('demo')"><text x="110" y="55">click me</text></a>
  <image xlink:href="https://tracker.example.com/pixel.png" width="10" height="10"/>
  <rect x="10" y="10" width="20" height="20"
        style="fill: red; background: url(https://tracker.example.com/bg.png)"/>
  <g inkscape:label="demo layer" inkscape:groupmode="layer">
    <path d="M 10 90 L 190 90" stroke="black"/>
  </g>
</svg>
"""

TRACKER = """<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="https://tracker.example.com/style.xsl"?>
<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120">
  <!-- tracking comment left by the source site -->
  <metadata><rdf:Description xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">demo</rdf:Description></metadata>
  <style>rect { fill: url(https://tracker.example.com/fill.png); }</style>
  <image href="https://tracker.example.com/beacon.png" width="1" height="1"/>
  <use href="https://other.example.com/sprite.svg#icon" width="40" height="40"/>
  <rect x="10" y="10" width="100" height="100" fill="gold"/>
</svg>
"""

CLEAN = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" viewBox="0 0 200 100">
  <title>Clean demo chart</title>
  <desc>Two bars and a label, with nothing hidden inside.</desc>
  <rect x="10" y="20" width="40" height="70" fill="teal"/>
  <rect x="60" y="40" width="40" height="50" fill="teal"/>
  <text x="10" y="15" font-family="sans-serif">Demo</text>
</svg>
"""


def main():
    here = Path(__file__).resolve().parent
    (here / "dirty.svg").write_text(DIRTY, encoding="utf-8")
    (here / "tracker.svg").write_text(TRACKER, encoding="utf-8")
    (here / "clean.svg").write_text(CLEAN, encoding="utf-8")
    print("wrote dirty.svg, tracker.svg, clean.svg")


if __name__ == "__main__":
    main()
