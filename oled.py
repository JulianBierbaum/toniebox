import time
import Adafruit_SSD1306
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

# Initialize the display
OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_RST = 24  # GPIO pin used for reset (check your setup)
OLED_DC = 23   # GPIO pin used for DC (check your setup)
OLED_CS = 8    # GPIO pin used for chip select (check your setup)

# Initialize the OLED display using I2C
disp = Adafruit_SSD1306.SSD1306_128_64(rst=OLED_RST, dc=OLED_DC, cs=OLED_CS)

# Initialize library (hardware reset)
disp.begin()

# Clear the display
disp.clear()
disp.display()

# Create an image object to draw on the display
image = Image.new('1', (OLED_WIDTH, OLED_HEIGHT))
draw = ImageDraw.Draw(image)

# Define the font and size (default font or load custom font)
font = ImageFont.load_default()

# Draw some text on the image
text = "Hello, Raspberry Pi!"
text_width, text_height = draw.textsize(text, font=font)
draw.text(((OLED_WIDTH - text_width) // 2, (OLED_HEIGHT - text_height) // 2), text, font=font, fill=255)

# Display the image on the OLED
disp.image(image)
disp.display()

# Pause for a few seconds
time.sleep(5)
