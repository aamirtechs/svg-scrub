# Good first issues

Seeded ideas for new contributors. Each one is small, tested, and safe
to take: open an issue or a pull request against this file's text.

## 1. Scan animate values that rewrite links

Problem: an `<animate>` element can change an attribute at runtime,
for example animating `xlink:href` from a safe value to a javascript:
URL after load, and svg-scrub only inspects the static value. Work:
when an animate/animateTransform/set element targets `href` (via
`attributeName`), inspect its `values`, `from`, `to` and `by`
attributes with the same unsafe-link rules and drop the element (or
just the offending value) when they match. Files: svg_scrub.py,
tests/test_svg_scrub.py, README.md (limitations section). Tests to
add: animate to a javascript: URL is removed, animate of a safe
attribute like opacity is kept, multi-value lists with one bad entry
are handled.

## 2. Add a --diff report showing bytes saved

Problem: users cannot see how much hidden content a file carried.
Work: add a `--diff` flag that prints, per file, the input size, output
size and bytes removed, plus a total line. Files: svg_scrub.py (report
dict gains `size_before`/`size_after`), tests/test_svg_scrub.py,
README.md. Tests to add: sizes match the real files, dry-run still
reports sizes without writing, JSON output includes the new fields.

## 3. Report the exact element path of each removal

Problem: the diff report counts removals per category but not where
they were, so a user fixing a source file must hunt. Work: record the
element path (for example `/svg/g[2]/script`) for each removal and
include a `removed_items` list in the JSON report only, keeping the
plain text output as counts. Files: svg_scrub.py (walk records paths),
tests/test_svg_scrub.py, README.md. Tests to add: paths match the
document structure, nested removals get distinct paths, JSON output
includes the list while text output stays unchanged.

## 4. Add a --keep-metadata option

Problem: some workflows want the editor metadata (author, license)
kept while still removing active content. Work: add
`--keep-metadata`, which skips the metadata category only, and a
`--keep` flag family if it stays readable. Files: svg_scrub.py,
tests/test_svg_scrub.py, README.md. Tests to add: metadata kept with
the flag, still removed without it, scripts still removed in both
modes.
