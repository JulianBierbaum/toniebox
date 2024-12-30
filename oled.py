from luma.core.interface.serial import i2c, spi
from luma.core.render import canvas
from luma.oled.device import sh1106
from PIL import ImageFont

def main():
    # Choose the communication interface (I2C or SPI)
    # Uncomment the appropriate line depending on your connection:
    
    # I2C interface (default address 0x3C or 0x3D)
    serial = i2c(port=1, address=0x3C)
    
    # SPI interface
    # serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25)
    
    # Create the SH1106 device instance
    device = sh1106(serial)
    
    # Display some text
    with canvas(device) as draw:
        # Load a custom font or use default
        # Custom font (optional)
        # font = ImageFont.truetype("arial.ttf", size=14)
        font = None  # Use default font
        
        # Draw text on the display
        draw.text((10, 10), "Hello, SH1106!", fill="white", font=font)
        draw.text((10, 30), "Raspberry Pi", fill="white", font=font)

    # Keep the display on for 10 seconds
    import time
    time.sleep(10)

if __name__ == "__main__":
    main()
