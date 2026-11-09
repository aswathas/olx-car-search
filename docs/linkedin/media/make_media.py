"""Render the two LinkedIn cards from real olxcars output."""
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(r"C:\Users\aswat\olx-car-search")
MEDIA = REPO / "docs" / "linkedin" / "media"
MEDIA.mkdir(parents=True, exist_ok=True)
FONT = r"C:\Windows\Fonts\consola.ttf"
FONT_B = r"C:\Windows\Fonts\consolab.ttf"

BG = (13, 17, 23)
CHROME = (22, 27, 34)
FG = (201, 209, 217)
DIM = (110, 118, 129)
GREEN = (63, 185, 80)
CYAN = (57, 197, 187)
YELLOW = (210, 153, 34)
BLUE = (121, 192, 255)


def run(*args):
    out = subprocess.run(["olxcars", *args], capture_output=True, text=True,
                         encoding="utf-8").stdout
    return json.loads(out)


def chrome(d, img, title):
    d.rectangle([0, 0, img.width, 64], fill=CHROME)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([28 + i * 34, 24, 44 + i * 34, 40], fill=c)
    d.text((img.width // 2 - 130, 20), title, font=ImageFont.truetype(FONT, 22), fill=DIM)


def card_one():
    data = run("search", "swift", "--city", "chennai", "--min-price", "300000",
               "--max-price", "600000", "--year-min", "2018", "--sort", "price_asc",
               "--limit", "8")
    W, H = 1200, 525
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    chrome(d, img, "olxcars  —  olx-car-search")
    f_title = ImageFont.truetype(FONT_B, 26)
    f_cmd = ImageFont.truetype(FONT, 19)
    f_out = ImageFont.truetype(FONT, 18)
    f_small = ImageFont.truetype(FONT, 16)

    d.text((48, 92), "Search OLX India used cars from a terminal", font=f_title, fill=FG)
    y = 140
    for parts in [
        [("$ ", GREEN), ("olxcars search ", FG), ('"swift"', YELLOW)],
        [("  --city chennai ", CYAN), ("--min-price 300000 --max-price 600000 ", CYAN),
         ("--year-min 2018 ", CYAN), ("--sort price_asc", CYAN)],
    ]:
        x = 48
        for text, color in parts:
            d.text((x, y), text, font=f_cmd, fill=color)
            x += d.textlength(text, font=f_cmd)
        y += 30
    y += 16
    for car in data["cars"][:6]:
        line = (f"{car['price_display']:>10}  {car.get('year') or '????'}  "
                f"{car.get('km') or 0:>6,} km  "
                f"{(car.get('make') or '') + ' ' + (car.get('model') or ''):<26.26}  "
                f"{(car.get('transmission') or ''):<10.10}  {(car.get('city') or '')[:8]}")
        d.text((48, y), line, font=f_out, fill=FG)
        y += 30
    y += 12
    d.text((48, y), f"20 of {data['total']:,} cars  ·  filters applied: "
                    f"{', '.join(data['filters_applied'])}", font=f_small, fill=DIM)
    y += 30
    d.text((48, y), "github.com/aswathas/olx-car-search", font=f_cmd, fill=CYAN)
    img.save(MEDIA / "01-hook.png")
    print("01-hook.png", img.size)


def card_two():
    data = run("search", "swift", "--city", "chennai", "--max-price", "600000",
               "--limit", "3")
    car = data["cars"][0]
    fields = ["id", "title", "price", "price_display", "year", "km", "fuel",
              "transmission", "owner", "city", "state", "lat", "lon", "seller", "url"]
    body = {k: car[k] for k in fields}
    text = json.dumps(body, indent=2, ensure_ascii=False)

    W, H = 1200, 700
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    chrome(d, img, "olxcars  —  --json")
    f_cmd = ImageFont.truetype(FONT, 18)
    f_small = ImageFont.truetype(FONT, 16)

    y = 96
    d.text((48, y), "$ olxcars search \"swift\" --city chennai --json", font=f_cmd, fill=GREEN)
    y += 40
    for line in text.splitlines():
        color = FG
        stripped = line.strip()
        if stripped.startswith('"'):
            key = stripped.split('"')[1]
            color = BLUE if key in fields else YELLOW
        elif stripped in ("{", "}", "[", "]", "},"):
            color = DIM
        d.text((48, y), line, font=f_cmd, fill=color)
        y += 26
    y += 14
    d.text((48, y), "one car, every field an agent needs to rank it", font=f_small, fill=DIM)
    img.save(MEDIA / "02-proof.png")
    print("02-proof.png", img.size)


card_one()
card_two()
