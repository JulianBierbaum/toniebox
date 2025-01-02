from luma.core.interface.serial import i2c, spi
from luma.core.render import canvas
from luma.oled.device import sh1106
from PIL import ImageFont

def main():
    serial = i2c(port=1, address=0x3C)
    
    device = sh1106(serial)
    
    with canvas(device) as draw:
        font = None
        
        draw.text((10, 10), "Raspberry Pi", fill="white", font=font)

    import time
    time.sleep(10)

if __name__ == "__main__":
    main()
