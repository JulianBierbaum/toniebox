import time
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522


def test_rfid():
    print("Initializing RFID Reader (MFRC522)...")
    reader = SimpleMFRC522()

    print(
        "Reader initialized. Please place a tag near the reader. Press Ctrl+C to exit."
    )

    try:
        while True:
            print("Waiting for tag...")
            id_val, text = reader.read()
            print("Tag Detected!")
            print(f"ID: {id_val}")
            print(f"Text: {text}")
            print("-" * 20)
            time.sleep(1)  # Prevent rapid re-reading

    except KeyboardInterrupt:
        print("\nTest cancelled by user.")
    except Exception as e:
        print(f"Error testing RFID reader: {e}")
    finally:
        GPIO.cleanup()
        print("GPIO cleaned up.")


if __name__ == "__main__":
    test_rfid()
