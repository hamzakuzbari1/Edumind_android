from pathlib import Path

from PIL import Image, ImageDraw


src = Path(__file__).resolve().parent
images = sorted(src.glob("student_v2-*.png"))
thumbs = []

for index, path in enumerate(images, 1):
    image = Image.open(path).convert("RGB")
    image.thumbnail((220, 312))
    tile = Image.new("RGB", (240, 350), "white")
    tile.paste(image, ((240 - image.width) // 2, 28))
    draw = ImageDraw.Draw(tile)
    draw.text((10, 8), f"Page {index}", fill=(0, 0, 0))
    thumbs.append(tile)

cols = 4
rows = (len(thumbs) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 240, rows * 350), (240, 240, 240))
for index, tile in enumerate(thumbs):
    sheet.paste(tile, ((index % cols) * 240, (index // cols) * 350))

output = src / "contact_sheet.png"
sheet.save(output)
print(output)
