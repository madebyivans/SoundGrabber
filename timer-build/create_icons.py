from PIL import Image, ImageDraw
import platform

# Determine the operating system
IS_MACOS = platform.system() == "Darwin"

def create_icon():
    size = 256  # larger size for better quality
    image = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    padding = 20
    circle_bbox = [padding, padding, size-padding, size-padding]
    center = size // 2
    
    draw.ellipse(circle_bbox, fill=(255, 255, 255, 255), outline=(64, 64, 64, 255), width=4)
    draw.line([center, center, center, center-size//3], fill=(64, 64, 64, 255), width=6)
    draw.line([center, center, center+size//3, center], fill=(64, 64, 64, 255), width=4)
    
    # Save PNG for both platforms
    image.save('icon.png', 'PNG')
    
    if IS_MACOS:
        # Save ICNS for macOS
        image.save('icon.icns', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    else:
        # Save ICO for Windows
        image.save('icon.ico', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])

if __name__ == "__main__":
    create_icon()