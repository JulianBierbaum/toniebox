import RPi.GPIO as GPIO
import time
import os
from dotenv import load_dotenv

load_dotenv()

CLK = int(os.getenv("ENCODER_CLK", 27))
DT = int(os.getenv("ENCODER_DT", 22))

GPIO.setmode(GPIO.BCM)
GPIO.setup(CLK, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(DT, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print(f"Monitoring pins CLK={CLK} and DT={DT} (Ctrl+C to stop)")
print("These are configured with PULL_UP. They should read 1 normally.")
print("If you rotate the encoder, they should briefly flicker to 0.")

try:
    last_clk = GPIO.input(CLK)
    last_dt = GPIO.input(DT)
    
    print(f"Initial State -> CLK: {last_clk}, DT: {last_dt}")
    
    while True:
        clk_state = GPIO.input(CLK)
        dt_state = GPIO.input(DT)
        
        if clk_state != last_clk or dt_state != last_dt:
            print(f"CHANGE detected! CLK: {clk_state}, DT: {dt_state}")
            last_clk = clk_state
            last_dt = dt_state
            
        time.sleep(0.001)

except KeyboardInterrupt:
    print("\nExiting...")
finally:
    GPIO.cleanup()
