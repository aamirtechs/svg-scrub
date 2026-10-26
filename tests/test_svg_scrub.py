"""Tests for svg_scrub.py. Run from the project root:

    python3 -m pytest tests/ -q
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import svg_scrub  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SVG = ('<svg xmlns="http://www.w3.org/2000/svg" '
       'xmlns:xlink="http://www.w3.org/1999/xlink" '
       'width="100" height="100">%s</svg>')


def scrub(body, **kwargs):
    text, counts = svg_scrub.sanitize(SVG % body, **kwargs)
    return text, counts


def test_script_removed():
    text, counts = scrub('<script>alert(1)</script><circle r="5"/>')
    assert "<script" not in text
    assert counts["script"] == 1
    assert "<circle" in text


def test_foreignobject_and_handler_removed():
    text, counts = scrub(
        '<foreignObject><div>x</div></foreignObject><handler/>')
    assert "foreignObject" not in text and "handler" not in text
    assert counts["foreignobject"] == 1 and counts["handler"] == 1


def test_event_handlers_removed():
    text, counts = scrub(
        '<circle r="5" onclick="go()" ONLOAD="go()" fill="red"/>')
    assert "onclick" not in text and "onload" not in text.lower()
    assert counts["event_handler"] == 2
    assert 'fill="red"' in text


def test_javascript_link_removed_but_http_link_kept():
    text, counts = scrub(
        '<a xlink:href="javascript:alert(1)"><text>x</text></a>'
        '<a href="https://example.com"><text>y</text></a>')
    assert "javascript:" not in text
    assert counts["unsafe_link"] == 1
    assert "https://example.com" in text


def test_external_image_dropped():
    text, counts = scrub(
        '<image xlink:href="https://tracker.example.com/p.png" '
        'width="10" height="10"/><circle r="5"/>')
    assert "<image" not in text
    assert counts["image"] == 1


def test_safe_data_image_kept_and_svg_data_dropped():
    text, counts = scrub(
        '<image href="data:image/png;base64,AAAA" width="10" height="10"/>'
        '<image href="data:image/svg+xml;base64,PHN2Zz4=" '
        'width="10" height="10"/>')
    assert "data:image/png" in text
    assert "data:image/svg" not in text
    assert counts["image"] == 1


def test_style_url_and_expression_removed():
    text, counts = scrub(
        '<rect style="fill: red; background: url(https://x.example.com/a.png)"/>'
        '<rect style="width: expression(alert(1))"/>'
        '<rect style="fill: blue"/>')
    assert "tracker" not in text and "expression(" not in text
    assert counts["style_url"] == 2
    assert 'style="fill: blue"' in text


def test_dangerous_style_element_dropped_safe_one_kept():
    text, counts = scrub(
        '<style>rect { fill: url(https://x.example.com/f.png); }</style>'
        '<style>circle { fill: red; }</style>')
    assert "x.example.com" not in text
    assert "circle { fill: red; }" in text
    assert counts["style_url"] == 1


def test_metadata_comment_pi_doctype_removed():
    data = ('<?xml version="1.0"?>\n<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" '
            '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n'
            '<?xml-stylesheet href="x"?>\n'
            + SVG % '<!-- note --><metadata>m</metadata><circle r="5"/>')
    text, counts = svg_scrub.sanitize(data.encode("utf-8"))
    assert "DOCTYPE" not in text and "<!--" not in text
    assert "xml-stylesheet" not in text and "<metadata" not in text
    assert counts["doctype"] == 1 and counts["comment"] == 1
    assert counts["processing_instruction"] == 1
    assert counts["metadata"] == 1


def test_title_and_desc_kept():
    text, counts = scrub(
        "<title>Chart</title><desc>Two bars.</desc><circle r='5'/>")
    assert "<title>Chart</title>" in text
    assert "<desc>Two bars.</desc>" in text


def test_editor_namespaces_kept_by_default_stripped_with_flag():
    body = ('<g xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
            'inkscape:label="layer"><circle r="5"/></g>')
    text, counts = scrub(body)
    assert "inkscape:label" in text
    assert counts.get("editor", 0) == 0
    text, counts = scrub(body, strip_editor=True)
    assert "inkscape" not in text
    assert counts["editor"] == 1


def test_external_use_href_removed():
    text, counts = scrub('<use href="https://x.example.com/s.svg#i"/>')
    assert "x.example.com" not in text
    assert counts["unsafe_link"] == 1


def test_clean_svg_unchanged_counts():
    text, counts = scrub('<circle r="5" fill="red"/>')
    assert counts == {}
    assert "<circle" in text


def test_malformed_xml_clean_error():
    with pytest.raises(ValueError, match="malformed XML"):
        svg_scrub.sanitize(b"<svg><circle></svg>")


def test_non_svg_root_clean_error():
    with pytest.raises(ValueError, match="not an SVG"):
        svg_scrub.sanitize(b"<html><body>x</body></html>")


def test_check_gate_exit_codes(tmp_path):
    dirty = tmp_path / "dirty.svg"
    dirty.write_text(SVG % '<script>alert(1)</script>', encoding="utf-8")
    clean = tmp_path / "clean.svg"
    clean.write_text(SVG % '<circle r="5"/>', encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(ROOT / "svg_scrub.py"), "--check",
         str(dirty), str(clean)],
        capture_output=True, text=True)
    assert r.returncode == 1
    assert "dangerous content found" in r.stdout
    r = subprocess.run(
        [sys.executable, str(ROOT / "svg_scrub.py"), "--check", str(clean)],
        capture_output=True, text=True)
    assert r.returncode == 0
    assert "clean" in r.stdout


def test_dry_run_writes_nothing_and_cleaning_writes(tmp_path):
    src = tmp_path / "a.svg"
    src.write_text(SVG % '<script>alert(1)</script><circle r="5"/>',
                   encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(ROOT / "svg_scrub.py"), "--dry-run", str(src)],
        capture_output=True, text=True)
    assert r.returncode == 0
    assert not list(tmp_path.glob("*.clean.svg"))
    r = subprocess.run(
        [sys.executable, str(ROOT / "svg_scrub.py"), str(src)],
        capture_output=True, text=True)
    assert r.returncode == 0
    out = tmp_path / "a.clean.svg"
    assert out.exists()
    assert "<script" not in out.read_text(encoding="utf-8")
    assert "<circle" in out.read_text(encoding="utf-8")


def test_in_place_and_out_dir_and_dir_batch(tmp_path):
    src = tmp_path / "b.svg"
    src.write_text(SVG % '<circle r="5" onclick="go()"/>', encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(ROOT / "svg_scrub.py"), "--in-place", str(src)],
        capture_output=True, text=True)
    assert r.returncode == 0
    assert "onclick" not in src.read_text(encoding="utf-8")

    dirty = tmp_path / "d.svg"
    dirty.write_text(SVG % '<script>alert(1)</script>', encoding="utf-8")
    out_dir = tmp_path / "out"
    r = subprocess.run(
        [sys.executable, str(ROOT / "svg_scrub.py"), "--dir", str(tmp_path),
         "--out-dir", str(out_dir)],
        capture_output=True, text=True)
    assert r.returncode == 0
    assert (out_dir / "d.clean.svg").exists()
    assert "<script" not in (out_dir / "d.clean.svg").read_text(encoding="utf-8")


def test_json_report_structure(tmp_path):
    src = tmp_path / "c.svg"
    src.write_text(SVG % '<script>alert(1)</script>', encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(ROOT / "svg_scrub.py"), "--check", "--json",
         str(src)],
        capture_output=True, text=True)
    report = json.loads(r.stdout)
    assert report["summary"]["files"] == 1
    assert report["summary"]["with_dangerous"] == 1
    assert report["files"][0]["removed"]["script"] == 1
    assert r.returncode == 1


def test_malformed_cli_no_traceback(tmp_path):
    bad = tmp_path / "bad.svg"
    bad.write_text("<svg><unclosed>", encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(ROOT / "svg_scrub.py"), "--check", str(bad)],
        capture_output=True, text=True)
    assert r.returncode == 2
    assert "Traceback" not in r.stderr and "Traceback" not in r.stdout
    assert "malformed XML" in r.stdout
