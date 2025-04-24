"""
RFID reader functionality for the RFID Audio Player.

This module provides a wrapper around the SimpleMFRC522 library
for reading RFID tags.
"""

from mfrc522 import SimpleMFRC522
import time
from threading import Event, Lock
import RPi.GPIO as GPIO

class RFIDReader:
    """
    A class to handle RFID tag reading operations.
    
    This class provides methods to read RFID tags and manage the
    active state of the reader.
    """
    
    def __init__(self):
        """Initialize the RFID reader."""
        self.reader = SimpleMFRC522()
        self.active = True
        self.cancel_event = Event()
        self.reader_lock = Lock()
        self.consecutive_errors = 0
        self.max_consecutive_errors = 3
        self.last_successful_read_time = time.time()
        self.reinit_interval = 10
    
    def read_tag(self):
        """
        Read an RFID tag and return its ID.
        
        Returns:
            tuple: (id, text) from the RFID tag
        """
        with self.reader_lock:
            try:
                return self.reader.read()
            except Exception as e:
                print(f"RFID read error: {e}")
                self._reset_reader()
                return None, None
    
    def read_tag_no_block(self):
        """
        Read an RFID tag without blocking if no tag is present.
        
        Returns:
            tuple: (id, text) from the RFID tag, or (None, None) if no tag
        """
        if time.time() - self.last_successful_read_time > self.reinit_interval:
            print("No successful reads for a while, proactively reinitializing reader...")
            self._reset_reader()
            self.last_successful_read_time = time.time()
            
        with self.reader_lock:
            try:
                id_val, text = self.reader.read_no_block()
                # Reset consecutive error counter and update timestamp on successful read
                if id_val is not None:
                    self.consecutive_errors = 0
                    self.last_successful_read_time = time.time()
                return id_val, text
            except Exception as e:
                print(f"RFID read_no_block error: {e}")
                self.consecutive_errors += 1
                
                # If we get too many consecutive errors, reset the reader
                if self.consecutive_errors >= self.max_consecutive_errors:
                    self._reset_reader()
                    self.consecutive_errors = 0
                    
                return None, None
    
    def _reset_reader(self):
        """Reset the RFID reader hardware."""
        try:
            # Clean up GPIO first
            GPIO.cleanup()
            # Reinitialize reader
            print("Reinitializing RFID reader...")
            time.sleep(0.5)  # Give hardware time to reset
            self.reader = SimpleMFRC522()
        except Exception as e:
            print(f"Error resetting RFID reader: {e}")
    
    def read_with_timeout(self, timeout=30, check_interval=0.1, max_retries=3):
        """
        Read an RFID tag with timeout and error handling.
        
        Args:
            timeout (float): Maximum time to wait in seconds (None for no timeout)
            check_interval (float): Interval between read attempts
            max_retries (int): Maximum number of retries on error
            
        Returns:
            tuple: (id, text) from the RFID tag, or (None, None) if timeout/cancelled
        """
        self.cancel_event.clear()
        start_time = time.time()
        retries = 0

        while True:
            # Check for timeout
            if timeout and (time.time() - start_time > timeout):
                print("RFID read timeout")
                return None, None
                
            # Check for cancellation
            if self.cancel_event.is_set():
                print("RFID read cancelled")
                return None, None

            with self.reader_lock:
                try:
                    # Try to read tag
                    id_val, text = self.reader.read_no_block()
                    if id_val is not None:
                        return id_val, text
                except Exception as e:
                    print(f"RFID read error: {e}")
                    retries += 1
                    if retries > max_retries:
                        print("Max retries reached, giving up.")
                        # Reset the reader before giving up
                        self._reset_reader()
                        return None, None
                    
                    # Reinitialize reader
                    self._reset_reader()
            
            time.sleep(check_interval)
    
    def cancel_read(self):
        """Cancel an ongoing read_with_timeout operation."""
        print("Cancelling RFID read")
        self.cancel_event.set()
