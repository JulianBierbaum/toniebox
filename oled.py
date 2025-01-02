from luma.core.interface.serial import i2c
from gpiozero import Button
from luma.core.render import canvas
from luma.oled.device import sh1106
from PIL import Image, ImageDraw, ImageFont
import time

button_up = Button(2)
button_down = Button(3)
button_select = Button(4)

serial = i2c(port=1, address=0x3C)
device = sh1106(serial)

font = ImageFont.load_default()

menu_items = ["Option 1", "Option 2", "Option 3", "Option 4"]
selected_index = 0

def main():
    with canvas(device) as draw:
        font = None  # Use default font
        
        draw.text((10, 10), "Raspberry Pi", fill="white", font=font)

    time.sleep(10)

if __name__ == "__main__":
    main()
