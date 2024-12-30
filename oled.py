import time
from adafruit_ssd1306 import SSD1306_I2C

# Define the screen dimensions
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64


# Create the display object
display = SSD1306_I2C(SCREEN_WIDTH, SCREEN_HEIGHT, i2c)

def reset_display():
    """Reset the OLED display by clearing and reinitializing."""
    print("Resetting display...")
    display.fill(0)  # Clear the display buffer
    display.show()   # Push cleared buffer to the display
    time.sleep(1)    # Wait for a second

    # Reinitialize display (soft reset)
    display.fill(0)
    display.text("OLED Reset Successful!", 0, 0, 1)
    display.show()

# Main program
try:
    reset_display()
    while True:
        # Example: periodically reset the display
        time.sleep(5)
        reset_display()
except KeyboardInterrupt:
    print("Program terminated.")
