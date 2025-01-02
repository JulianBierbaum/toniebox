from gpiozero import Button
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from PIL import Image, ImageDraw, ImageFont
import time

# Initialize buttons
button_up = Button(2)
button_down = Button(3)
button_select = Button(4)

# Initialize OLED display
serial = i2c(port=1, address=0x3C)
device = sh1106(serial)

# Load font
font = ImageFont.load_default()

# Menu options
menu_items = ["Option 1", "Option 2", "Option 3", "Option 4"]
selected_index = 0

def draw_menu():
    """Draws the menu on the OLED display."""
    with Image.new("1", (device.width, device.height)) as image:
        draw = ImageDraw.Draw(image)
        for i, item in enumerate(menu_items):
            y = i * 10
            if i == selected_index:
                draw.rectangle((0, y, device.width, y + 10), outline=255, fill=255)
                draw.text((2, y), item, font=font, fill=0)  # Inverted text
            else:
                draw.text((2, y), item, font=font, fill=255)
        device.display(image)

def update_selection():
    """Updates the selected menu item based on button presses."""
    global selected_index
    if button_up.is_pressed:
        selected_index = (selected_index - 1) % len(menu_items)
        time.sleep(0.2)  # Debounce delay
    elif button_down.is_pressed:
        selected_index = (selected_index + 1) % len(menu_items)
        time.sleep(0.2)  # Debounce delay
    elif button_select.is_pressed:
        print(f"Selected: {menu_items[selected_index]}")
        time.sleep(0.2)  # Debounce delay

# Main loop
try:
    while True:
        update_selection()
        draw_menu()
        time.sleep(0.1)  # Slight delay to reduce CPU usage
except KeyboardInterrupt:
    print("Exiting program.")
