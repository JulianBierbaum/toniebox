import os
import time
from gpiozero import Button, RotaryEncoder
from dotenv import load_dotenv

load_dotenv()

class EncoderTester:
    def __init__(self):
        self.clk = os.getenv("ENCODER_CLK")
        self.dt = os.getenv("ENCODER_DT")
        self.confirm_pin = os.getenv("ENCODER_CONFIRM")
        self.bounce_time = float(os.getenv("ENCODER_BOUNCE_TIME", 0.02))
        
        self.confirmed = False
        
        if not all([self.clk, self.dt, self.confirm_pin]):
            raise ValueError("Encoder pins not defined in .env file.")

        print(f"Initializing Encoder on pins: CLK={self.clk}, DT={self.dt}, SW={self.confirm_pin}")
        print(f"Using bounce_time: {self.bounce_time}")

        self.encoder = RotaryEncoder(int(self.clk), int(self.dt), bounce_time=self.bounce_time)
        self.button = Button(int(self.confirm_pin), bounce_time=self.bounce_time)

        # Production-style event callbacks
        self.encoder.when_rotated = self.handle_rotation
        self.button.when_pressed = self.handle_press

    def handle_rotation(self):
        steps = self.encoder.steps
        if steps != 0:
            direction = "Clockwise" if steps > 0 else "Counter-clockwise"
            print(f"Rotated! Direction: {direction}, Steps: {steps}")
            # Production resets steps after handling
            self.encoder.steps = 0

    def handle_press(self):
        print("Button Pressed! (on_confirm_pressed logic)")
        self.confirmed = True

    def run(self):
        print("Testing Encoder. Rotate or press the knob. Press Ctrl+C to exit.")
        try:
            while True:
                if self.confirmed:
                    print("Logic check: confirmed flag was set.")
                    self.confirmed = False
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nTest cancelled by user.")

def test_encoder():
    try:
        tester = EncoderTester()
        tester.run()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_encoder()