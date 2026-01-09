import os
import time
from gpiozero import Button, RotaryEncoder
from dotenv import load_dotenv

load_dotenv()

def test_encoder():
    clk = os.getenv("ENCODER_CLK")
    dt = os.getenv("ENCODER_DT")
    confirm = os.getenv("ENCODER_CONFIRM")
    
    print(f"Testing Encoder on pins: CLK={clk}, DT={dt}, SW={confirm}")
    
    if not all([clk, dt, confirm]):
        print("Error: Encoder pins not defined in .env file.")
        return

    try:
        bounce_time = float(os.getenv("ENCODER_BOUNCE_TIME", 0.05))
        encoder = RotaryEncoder(int(clk), int(dt), bounce_time=bounce_time)
        button = Button(int(confirm), bounce_time=bounce_time)
        
        print(f"Encoder initialized with bounce_time={bounce_time}. Rotate or press the knob. Press Ctrl+C to exit.")
        
        last_steps = 0
        
        while True:
            current_steps = encoder.steps
            if current_steps != last_steps:
                print(f"Rotated! Steps: {current_steps} (Delta: {current_steps - last_steps})")
                last_steps = current_steps
                
            if button.is_pressed:
                print("Button Pressed!")
                while button.is_pressed:
                    time.sleep(0.1) # Wait for release
                print("Button Released")
                
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\nTest cancelled by user.")
    except Exception as e:
        print(f"Error testing encoder: {e}")

if __name__ == "__main__":
    test_encoder()
