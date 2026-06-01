#!/usr/bin/env python3
from PIL import Image

# Load the image
img = Image.open("edna_children_grandchildren.jpg")

# Add 700 pixel black border
border_size = 700
bordered_img = Image.new('RGB', (img.width + 2*border_size, img.height + 2*border_size), color='black')
bordered_img.paste(img, (border_size, border_size))

# Save to i.jpg
bordered_img.save("i.jpg", quality=95)

print(f"Original size: {img.width}x{img.height}")
print(f"New size: {bordered_img.width}x{bordered_img.height}")
print("Saved to i.jpg")
