"""Create the original 1200x630 share card using Pillow and Windows fonts."""
from pathlib import Path
import math
import random
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONTS = Path('C:/Windows/Fonts')
WIDTH, HEIGHT = 1200, 630


def font(size, bold=False, latin=False):
    name = 'georgia.ttf' if latin else ('msjhbd.ttc' if bold else 'msjh.ttc')
    return ImageFont.truetype(str(FONTS / name), size)


def create():
    random.seed(18)
    image = Image.new('RGB', (WIDTH, HEIGHT))
    pixels = image.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            glow = max(0, 1 - math.hypot((x - 970) / 800, (y - 270) / 650))
            grain = random.choice([-1, 0, 0, 1])
            pixels[x, y] = (int(17 + glow * 10) + grain, int(21 + glow * 12) + grain, int(20 + glow * 4) + grain)
    draw = ImageDraw.Draw(image)
    gold, cream, muted = '#cfb17a', '#eceade', '#929e85'
    draw.rectangle((25, 25, 1174, 604), outline='#454b37', width=1)
    draw.line((70, 116, 1130, 116), fill='#343b31', width=1)
    draw.text((76, 61), '永恆 / 專業議事廳', font=font(23, True), fill=cream)
    draw.text((810, 65), 'WORLD OF WARCRAFT · FOREVER', font=font(13, latin=True), fill=gold)
    draw.text((76, 149), '全專業分工 × 傳承里程碑', font=font(16), fill=gold)
    draw.text((72, 196), '五隻角色，', font=font(53, True), fill=cream)
    draw.text((72, 272), '建立你的專業版圖。', font=font(53, True), fill='#edcf94')
    draw.text((78, 362), '三種養成路線，從第一個包包開始。', font=font(20), fill=muted)
    cx, cy = 961, 287
    for radius, line in [(175, '#51472e'), (149, '#76623b'), (137, '#373d2b')]:
        draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), outline=line, width=1)
    draw.line((cx-194, cy+141, cx+194, cy-141), fill='#3c3e2b')
    draw.line((cx-194, cy-141, cx+194, cy+141), fill='#3c3e2b')
    draw.ellipse((cx-99, cy-99, cx+99, cy+99), fill='#1b211a')
    draw.text((cx, cy-36), '18', font=font(98, latin=True), fill='#edcf94', anchor='mm')
    draw.text((cx, cy+40), '製造傳承點數', font=font(18), fill=cream, anchor='mm')
    for angle, glyph, color in [(-90, '聖', '#dda6bc'), (-18, '法', '#85c9d5'), (54, '德', '#db9b5a'), (126, '獵', '#a8c486'), (198, '賊', '#ded187')]:
        x = cx + math.cos(math.radians(angle)) * 149
        y = cy + math.sin(math.radians(angle)) * 149
        draw.rectangle((x-20, y-23, x+20, y+23), fill='#111514', outline=color)
        draw.text((x, y), glyph, font=font(22, True), fill=color, anchor='mm')
    draw.line((76, 444, 1124, 444), fill='#424932')
    for x, number, label in [(78, '05', '不同職業'), (328, '09', '主要專業'), (578, '18', '製造里程碑點數')]:
        draw.text((x, 473), number, font=font(42, latin=True), fill=gold)
        draw.text((x+74, 489), label, font=font(17), fill=cream)
    draw.text((78, 558), 'blog.jakeuj.com/wow-forever-professions', font=font(14, latin=True), fill=muted)
    draw.text((1130, 558), 'zh-TW / 2026.11.11', font=font(13, latin=True), fill=muted, anchor='ra')
    destination = ROOT / 'assets' / 'social-v1.png'
    image.save(destination, optimize=True)
    print(f'{destination} ({WIDTH}x{HEIGHT})')


if __name__ == '__main__':
    create()
