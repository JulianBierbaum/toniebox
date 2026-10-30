import time
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106
from PIL import ImageFont


def test_display():
    print("Initializing OLED display on I2C port 1, address 0x3C...")
    try:
        serial = i2c(port=1, address=0x3C)
        device = sh1106(serial)
        font = ImageFont.load_default()

        print("Display initialized. Drawing test pattern...")

        # Draw a test pattern
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="black")
            draw.text((10, 10), "Display Test", font=font, fill="white")
            draw.text((10, 30), "Working!", font=font, fill="white")

        print("Test pattern drawn. Displaying for 5 seconds...")
        time.sleep(5)

        print("Clearing display...")
        with canvas(device) as draw:
            pass  # Clear

        print("Display test complete.")

    except Exception as e:
        print(f"Error initializing or using display: {e}")


if __name__ == "__main__":
    test_display()
