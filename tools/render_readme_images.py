"""Compose SVG artwork and render genuine Textual captures with local fonts.

Run after capture_screenshots.py with uv run --locked --group images.
Sources and crop metadata stay in captures/; public PNGs go to docs/images/.
No network resources, raster retouching, or live process data are used.
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path
import re
import subprocess
from xml.etree import ElementTree as ET

import resvg_py

CAPTURES = Path('captures')
OUTPUT = Path('docs/images')
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
BG, PANEL, LINE = '#0b1018', '#111c29', '#2b3d50'
INK, MUTED, ACCENT = '#ecf4ff', '#a1b2c7', '#61d6b2'
FONT = 'DejaVu Sans'
LANGUAGES = (('it', 'Italiano'), ('en', 'English'), ('zh', '简体中文'),
             ('ko', '한국어'), ('fr', 'Français'), ('vi', 'Tiếng Việt'),
             ('es', 'Español'), ('pt', 'Português'), ('de', 'Deutsch'), ('ja', '日本語'))


def text(x, y, value, size=24, fill=INK, weight=400, family=FONT):
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}">{escape(value)}</text>')


def rect(x, y, width, height, fill, radius=0, stroke='none'):
    return (f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
            f'rx="{radius}" fill="{fill}" stroke="{stroke}"/>')


def terminal(name, x, y, width, *, first_rows=None):
    """Keep Rich's cell positions, optionally cropping whole rows."""
    meta = json.loads((CAPTURES / f'{name}.json').read_text(encoding='utf-8'))
    if not meta['synthetic']:
        raise ValueError('Only synthetic captures may be published')
    root = ET.fromstring((CAPTURES / f'{name}.svg').read_text(encoding='utf-8'))
    style, defs = root.find(f'{{{NS}}}style'), root.find(f'{{{NS}}}defs')
    # Remove CDN fonts and desktop controls; retain the actual terminal render.
    style.text = re.sub(r'@font-face\s*\{[^}]*\}', '', style.text)
    style.text = style.text.replace('Fira Code, monospace', 'DejaVu Sans Mono, Noto Sans CJK SC, monospace')
    layer = next(child for child in root if child.get('clip-path', '').endswith('-clip-terminal)'))
    layer.attrib.pop('transform')
    clip = next(child for child in defs if child.get('id', '').endswith('-clip-terminal'))[0]
    cell_w = float(clip.get('width')) / meta['columns']
    cell_h = float(clip.get('height')) / meta['rows']
    cx, cy, cw, ch = meta['crop']
    if first_rows is not None:
        ch = min(ch, first_rows)
    height = width * ch * cell_h / (cw * cell_w)
    frame = ET.Element(f'{{{NS}}}svg', {
        'x': str(x), 'y': str(y), 'width': str(width), 'height': str(height),
        'viewBox': f'{cx * cell_w} {cy * cell_h} {cw * cell_w} {ch * cell_h}',
    })
    frame.extend((style, defs, ET.Element(f'{{{NS}}}rect', {
        'width': str(meta['columns'] * cell_w), 'height': str(meta['rows'] * cell_h),
        'fill': '#272727',
    }), layer))
    return ET.tostring(frame, encoding='unicode'), height


def write(name, width, height, content):
    svg = (f'<svg xmlns="{NS}" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}">'
           '<title>ramtaskman — synthetic demonstration</title>'
           + rect(0, 0, width, height, BG) + ''.join(content) + '</svg>')
    (CAPTURES / f'artwork-{name}.svg').write_text(svg, encoding='utf-8')
    png = resvg_py.svg_to_bytes(svg_string=svg, font_family=FONT,
                                monospace_family='DejaVu Sans Mono')
    (OUTPUT / f'{name}.png').write_bytes(png)
    print(f'{name}.png: {width} × {height}, {len(png):,} bytes')


def card(name, source, number, title, subtitle, *, first_rows=None):
    body, h = terminal(source, 40, 144, 1520, first_rows=first_rows)
    height = round(h + 216)
    write(name, 1600, height, [
        text(40, 44, f'RAMTASKMAN  /  {number}', 19, ACCENT, 700),
        text(40, 91, title, 36, weight=700),
        text(40, 124, subtitle, 20, MUTED),
        rect(39, 143, 1522, h + 2, PANEL, 2, LINE), body,
        text(40, height - 26, 'Textual on Linux · synthetic data · MIT · UI adapted from GPU Taskman', 18, MUTED),
    ])


def cover():
    body, h = terminal('gallery-overview', 40, 280, 1520, first_rows=29)
    height = round(h + 352)
    content = [text(42, 45, 'VIBEWARE  /  MEMORY EXPLORER', 20, ACCENT, 700),
               text(36, 139, 'ramtaskman', 92, weight=700),
               text(42, 193, 'See where your RAM goes.', 32, MUTED)]
    for index, label in enumerate(('Linux + Windows', '10 languages', 'MIT license')):
        x = 42 + index * 260
        content.extend((rect(x, 219, 244, 37, PANEL, 18, LINE), text(x + 18, 245, label, 21)))
    # Decorative vector motif, not a measurement.
    for index, (w, color) in enumerate(((120, '#60a5fa'), (75, ACCENT), (45, '#a78bfa'))):
        x = (1220, 1348, 1431)[index]
        content.append(rect(x, 78, w, 78, color, 8))
    content.extend((rect(39, 279, 1522, h + 2, PANEL, 2, LINE), body,
                    text(40, height - 39, 'Live Textual UI · synthetic data · dashboard and table excerpt', 18, MUTED),
                    text(40, height - 14, 'macOS experimental, not validated · UI adapted from Scott Hanselman’s GPU Taskman', 17, MUTED)))
    write('cover', 1600, height, content)


def multilingual():
    content = [text(40, 48, 'RAMTASKMAN  /  LANGUAGES', 20, ACCENT, 700),
               text(40, 105, 'One terminal. Ten languages.', 42, weight=700)]
    for index, (_, label) in enumerate(LANGUAGES):
        x, y = 40 + index % 5 * 306, 140 + index // 5 * 70
        content.extend((rect(x, y, 288, 54, PANEL, 10, LINE),
                        text(x + 18, y + 36, label, 25, family='Noto Sans CJK SC')))
    y = 305
    for code, label in (('en', 'ENGLISH'), ('ja', '日本語')):
        content.append(text(40, y, label, 21, ACCENT, 700, 'Noto Sans CJK SC'))
        body, h = terminal(f'gallery-language-{code}', 40, y + 16, 1520)
        content.extend((rect(39, y + 15, 1522, h + 2, PANEL, 2, LINE), body))
        y += h + 70
    content.append(text(40, y, 'System-panel excerpts · synthetic Linux data · translations await native-speaker review', 19, MUTED))
    write('multilingual', 1600, round(y + 32), content)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for family in ('DejaVu Sans', 'DejaVu Sans Mono', 'Noto Sans CJK SC'):
        found = subprocess.check_output(['fc-match', '-f', '%{family}', family], text=True)
        if family not in found:
            raise SystemExit(f'Missing font: {family}. See docs/images/README.md')
    cover()
    card('overview', 'gallery-overview', '01', 'Applications at a glance',
         'System RAM, history and per-application measurements.')
    card('full-diagnostics', 'gallery-full', '02', 'Every counter has a meaning',
         'Full diagnostics · system-panel excerpt · complete USS groups shown separately.')
    card('regions-resident', 'gallery-regions', '03', 'Explore a process',
         'Dashboard and table excerpt · virtual mappings and resident memory · metadata only.', first_rows=29)
    card('regions-comparison', 'gallery-comparison', '04', 'Compare two captures',
         'A → B · dashboard and table excerpt · growth is not proof of a leak.', first_rows=29)
    multilingual()


if __name__ == '__main__':
    main()
