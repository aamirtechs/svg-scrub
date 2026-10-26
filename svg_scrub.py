#!/usr/bin/env python3
"""svg-scrub: sanitize SVG files and report exactly what was removed.

Zero dependencies, Python 3.9+. SVG files pasted from the web often carry
scripts, event handlers, foreignObject embeds, external images, tracking
references and editor metadata. Browsers and design tools run that
content. svg-scrub parses the SVG with xml.etree, removes the dangerous
parts, keeps every safe drawing element and attribute, and prints a diff
report: counts removed per category.

What is removed, always:
  script, foreignObject and handler elements; metadata elements;
  comments, processing instructions and the DOCTYPE declaration;
  on* event handler attributes; javascript: and data:text/html links;
  external <image> references (only safe raster data URIs are kept);
  style attributes and <style> blocks that reference external URLs or
  use expression(); external <use> references.
What is kept: title and desc (accessibility), all safe drawing elements
and attributes, and safe data URI images.
What --strip-editor adds: inkscape and sodipodi elements and attributes.

The tool never modifies the input file unless --in-place is given; by
default cleaned copies are written next to the inputs with a ".clean"
suffix (or into --out-dir). Malformed XML produces a clean error
message, never a traceback.
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

VERSION = "1.0.0"

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
EDITOR_NS = {
    "http://www.inkscape.org/namespaces/inkscape",
    "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd",
}

# Elements dropped wholesale, by local name.
DANGEROUS_ELEMENTS = {"script", "foreignobject", "handler"}
# Raster data URI types allowed on <image>. Anything else (including
# data:image/svg+xml, which can carry its own script) is dropped.
SAFE_DATA_IMAGE = re.compile(r"^data:image/(png|jpe?g|gif|webp);", re.I)
# URL inside a style value that makes the style dangerous.
DANGEROUS_STYLE_URL = re.compile(
    r"url\(\s*['\"]?\s*(https?:|//|javascript:|data:text)", re.I
)
UNSAFE_LINK = re.compile(r"^\s*(javascript:|vbscript:|data:text/html)", re.I)

ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)
ET.register_namespace("inkscape", "http://www.inkscape.org/namespaces/inkscape")
ET.register_namespace(
    "sodipodi", "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
)


def _local(tag):
    """Local name of an element or attribute tag, lowercased."""
    if not isinstance(tag, str):
        return ""
    name = tag.rsplit("}", 1)[-1]
    return name.lower()


def _ns(tag):
    """Namespace URI of a tag, or ''."""
    if isinstance(tag, str) and tag.startswith("{"):
        return tag[1:].split("}", 1)[0]
    return ""


def _is_dangerous_style(value):
    return (
        "expression(" in value.lower()
        or bool(DANGEROUS_STYLE_URL.search(value))
        or "@import" in value.lower()
    )


def sanitize(data, strip_editor=False):
    """Sanitize one SVG document given as bytes.

    Returns (cleaned_text, counts) where counts maps each removed
    category to how many items were removed. Raises ValueError with a
    plain message on malformed XML or a non-SVG root element.
    """
    counts = {}
    if isinstance(data, str):
        data = data.encode("utf-8")
    # ElementTree drops the prolog (before the root element) without
    # reporting it, so count prolog comments and processing instructions
    # here. In-document ones are counted by the tree walk below.
    root_match = re.search(rb"<(?:[A-Za-z_][\w.-]*:)?svg(?=[\s>/])", data)
    if root_match:
        prolog = data[:root_match.start()]
        comments = len(re.findall(rb"<!--", prolog))
        if comments:
            counts["comment"] = comments
        pis = len(re.findall(rb"<\?", prolog))
        pis -= len(re.findall(rb"<\?xml(?=[\s?])", prolog))
        if pis:
            counts["processing_instruction"] = pis
    if re.search(rb"<!DOCTYPE", data):
        counts["doctype"] = 1

    def bump(category, n=1):
        counts[category] = counts.get(category, 0) + n

    builder = ET.TreeBuilder(insert_comments=True, insert_pis=True)
    parser = ET.XMLParser(target=builder)
    try:
        root = ET.fromstring(data, parser=parser)
    except ET.ParseError as exc:
        raise ValueError("malformed XML: %s" % exc) from None
    if _local(root.tag) != "svg":
        raise ValueError("not an SVG file (root element is <%s>)" % _local(root.tag))

    # Build a parent map (ElementTree has no parent pointers).
    parent = {}
    for par in root.iter():
        for child in list(par):
            parent[child] = par

    dropped = set()

    def drop(elem, category):
        par = parent.get(elem)
        if par is not None:
            par.remove(elem)
            bump(category)
            dropped.add(id(elem))
        elif elem is root:
            raise ValueError("root element itself is not allowed")

    def is_detached(elem):
        node = elem
        while node is not None:
            if id(node) in dropped:
                return True
            node = parent.get(node)
        return False

    # Walk a snapshot: removals during iteration must not skip siblings.
    # Children of an already dropped element are skipped, so one removed
    # element is never counted twice through its descendants.
    for elem in list(root.iter()):
        if is_detached(elem):
            continue
        tag = _local(elem.tag)
        if elem.tag is ET.Comment:
            drop(elem, "comment")
            continue
        if elem.tag is ET.PI:
            drop(elem, "processing_instruction")
            continue
        if tag in DANGEROUS_ELEMENTS:
            drop(elem, tag)
            continue
        if tag == "metadata":
            drop(elem, "metadata")
            continue
        if strip_editor and _ns(elem.tag) in EDITOR_NS:
            drop(elem, "editor")
            continue
        if tag == "style" and elem.text and _is_dangerous_style(elem.text):
            drop(elem, "style_url")
            continue
        # Attribute scrub, on a snapshot of the attribute names.
        for attr in list(elem.attrib):
            local = _local(attr)
            if local.startswith("on") and len(local) > 2:
                del elem.attrib[attr]
                bump("event_handler")
                continue
            if strip_editor and _ns(attr) in EDITOR_NS:
                del elem.attrib[attr]
                bump("editor")
                continue
            if local == "style" and _is_dangerous_style(elem.attrib[attr]):
                del elem.attrib[attr]
                bump("style_url")
                continue
            if local == "href":
                value = elem.attrib[attr].strip()
                if UNSAFE_LINK.match(value):
                    del elem.attrib[attr]
                    bump("unsafe_link")
                    continue
                if tag == "image":
                    if not SAFE_DATA_IMAGE.match(value):
                        drop(elem, "image")
                        break
                elif tag == "use":
                    if value.startswith(("http://", "https://", "//")):
                        del elem.attrib[attr]
                        bump("unsafe_link")
                        continue
    text = ET.tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + text, counts


def _describe(counts):
    parts = ["%s x%d" % (name, n) for name, n in sorted(counts.items())]
    return ", ".join(parts)


def _process(path, args):
    """Sanitize one file. Returns a result dict, never raises for bad XML."""
    try:
        data = path.read_bytes()
    except OSError as exc:
        return {"file": str(path), "error": str(exc), "removed": {},
                "total_removed": 0}
    try:
        cleaned, counts = sanitize(data, strip_editor=args.strip_editor)
    except ValueError as exc:
        return {"file": str(path), "error": str(exc), "removed": {},
                "total_removed": 0}
    total = sum(counts.values())
    result = {"file": str(path), "removed": counts, "total_removed": total}
    if total == 0:
        result["output"] = None
        return result
    if args.check or args.dry_run:
        result["output"] = None
        return result
    if args.in_place:
        out = path
    elif args.out_dir:
        out = Path(args.out_dir) / (path.stem + args.suffix + ".svg")
    else:
        out = path.with_name(path.stem + args.suffix + ".svg")
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(cleaned, encoding="utf-8")
    except OSError as exc:
        result["error"] = str(exc)
        result["output"] = None
        return result
    result["output"] = str(out)
    return result


def _collect(args):
    files = [Path(p) for p in args.files]
    for d in args.dir or []:
        root = Path(d)
        if not root.is_dir():
            print("error: not a directory: %s" % d, file=sys.stderr)
            sys.exit(2)
        files.extend(sorted(root.rglob("*.svg")))
    seen, unique = set(), []
    for f in files:
        key = str(f)
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="svg-scrub",
        description="Sanitize SVG files and report what was removed.",
    )
    parser.add_argument("files", nargs="*", help="SVG files to sanitize")
    parser.add_argument("--dir", action="append", metavar="DIR",
                        help="sanitize a folder recursively (repeatable)")
    parser.add_argument("--out-dir", metavar="DIR",
                        help="write cleaned copies here instead of next to the inputs")
    parser.add_argument("--suffix", default=".clean",
                        help="suffix for cleaned copies (default: .clean)")
    parser.add_argument("--in-place", action="store_true",
                        help="overwrite the input files")
    parser.add_argument("--strip-editor", action="store_true",
                        help="also strip inkscape/sodipodi elements and attributes")
    parser.add_argument("--check", action="store_true",
                        help="report only, exit 1 if any file has dangerous content")
    parser.add_argument("--dry-run", action="store_true",
                        help="show what would be removed, write nothing")
    parser.add_argument("--json", action="store_true",
                        help="print the full report as JSON")
    parser.add_argument("--report", metavar="PATH",
                        help="write the full report as JSON to a file")
    parser.add_argument("--version", action="version", version="svg-scrub " + VERSION)
    args = parser.parse_args(argv)

    files = _collect(args)
    if not files:
        print("error: no input files (pass SVG files or --dir)", file=sys.stderr)
        return 2

    results = [_process(f, args) for f in files]
    with_dangerous = sum(1 for r in results if r["total_removed"] > 0)
    total_removed = sum(r["total_removed"] for r in results)
    report = {
        "files": results,
        "summary": {
            "files": len(results),
            "with_dangerous": with_dangerous,
            "removed": total_removed,
        },
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for r in results:
            if r.get("error"):
                print("%s: error: %s" % (r["file"], r["error"]))
            elif r["total_removed"] == 0:
                print("%s: clean" % r["file"])
            elif args.check or args.dry_run:
                print("%s: %s [dangerous content found]"
                      % (r["file"], _describe(r["removed"])))
            elif r["output"]:
                print("%s -> %s [removed %s]"
                      % (r["file"], r["output"], _describe(r["removed"])))
            else:
                print("%s: %s" % (r["file"], _describe(r["removed"])))
        print("done: %d file(s), %d with dangerous content, %d item(s) removed"
              % (len(results), with_dangerous, total_removed))
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")

    errors = sum(1 for r in results if r.get("error"))
    if errors:
        return 2
    if args.check and with_dangerous:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
