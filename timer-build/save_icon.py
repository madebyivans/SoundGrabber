# save_icon.py
from PIL import Image, ImageDraw

def create_icon():
    size = 256  # larger size for better quality
    image = Image.new('RGBA', (size, size), color=(0,0,0,0))  # transparent background
    dc = ImageDraw.Draw(image)
    
    # Draw white circle with black border
    dc.ellipse([10, 10, size-10, size-10], fill='white', outline='black', width=4)
    
    # Draw clock hands
    center = size // 2
    # Hour hand
    dc.line([center, center, center, center-size//3], fill='black', width=6)
    # Minute hand
    dc.line([center, center, center+size//3, center], fill='black', width=4)
    
    image.save('icon.png', 'PNG')
    image.save('icon.ico', 'ICO')

create_icon()