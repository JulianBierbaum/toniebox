import RPi.GPIO as GPIO
import time

# List of standard GPIO pins (BCM numbering) on Raspberry Pi
# Excluding power/ground pins.
ALL_PINS = [
    2,
    3,
    4,
    17,
    27,
    22,
    10,
    9,
    11,
    5,
    6,
    13,
    19,
    26,
    14,
    15,
    18,
    23,
    24,
    25,
    8,
    7,
    12,
    16,
    20,
    21,
]

GPIO.setmode(GPIO.BCM)

# Store initial states
pin_states = {}
failed_pins = []

print("Setting up pins...")
for pin in ALL_PINS:
    try:
        # Configure as Input with Pull Up (assuming active-low logic like the encoder)
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        pin_states[pin] = GPIO.input(pin)
    except Exception:
        print(f"Skipping Pin {pin} (busy or unavailable)")
        failed_pins.append(pin)

# Remove failed pins from monitoring list
for p in failed_pins:
    ALL_PINS.remove(p)

print("\n--- PIN MONITOR STARTED ---")
print("Rotate your encoder now.")
print("I will tell you if ANY pin changes state.")
print("Press Ctrl+C to stop.\n")

try:
    while True:
        for pin in ALL_PINS:
            val = GPIO.input(pin)
            if val != pin_states[pin]:
                print(f"ACTIVITY DETECTED! Pin {pin} changed to {val}")
                pin_states[pin] = val

        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nStopped.")
finally:
    GPIO.cleanup()
