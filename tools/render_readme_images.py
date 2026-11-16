"""Render Linux Textual captures as PNGs; needs CairoSVG, Pillow and Noto CJK.

Run after capture_screenshots.py with a suitable temporary tooling environment.
All inputs use synthetic fixtures, never live process metadata.
"""
from pathlib import Path
import subprocess

import cairosvg
from PIL import Image, ImageDraw, ImageFont

CAPTURES = Path('captures')
OUTPUT = Path('docs/images')
LANGUAGES = (('it', 'ITALIANO'), ('en', 'ENGLISH'), ('zh', '中文'),
             ('ko', '한국어'), ('fr', 'FRANÇAIS'), ('vi', 'TIẾNG VIỆT'))


def render(name: str, destination: Path) -> None:
    svg = (CAPTURES / f'{name}.svg').read_text(encoding='utf-8')
    svg = svg.replace('font-family: Fira Code, monospace;', 'font-family: "Noto Sans Mono CJK SC";')
    cairosvg.svg2png(bytestring=svg.encode('utf-8'), write_to=str(destination))


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name in ('overview', 'full-diagnostics', 'regions-resident'):
        render(name, OUTPUT / f'{name}.png')
    for language, _ in LANGUAGES:
        render(f'language-{language}', CAPTURES / f'language-{language}.png')
    width, height = 1200, 433
    canvas = Image.new('RGB', (2 * width + 60, 3 * (height + 55) + 80), '#0d1117')
    draw = ImageDraw.Draw(canvas)
    font_path = subprocess.check_output(['fc-match', '-f', '%{file}', 'Noto Sans CJK SC'], text=True)
    font = ImageFont.truetype(font_path, 25)
    for index, (language, title) in enumerate(LANGUAGES):
        x = 20 + (index % 2) * (width + 20)
        y = 20 + (index // 2) * (height + 55 + 20)
        draw.text((x + 8, y), title, font=font, fill='#c9d1d9')
        with Image.open(CAPTURES / f'language-{language}.png') as image:
            # Crop to the dashboard and table for legibility; the pixels are unmodified captures.
            image = image.convert('RGB').crop((0, 0, 1970, 710))
            canvas.paste(image.resize((width, height), Image.Resampling.LANCZOS), (x, y + 42))
    canvas.save(OUTPUT / 'multilingual.png', optimize=True)


if __name__ == '__main__':
    main()
