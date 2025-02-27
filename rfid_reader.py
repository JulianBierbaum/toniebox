"""
RFID reader functionality for the RFID Audio Player.

This module provides a wrapper around the SimpleMFRC522 library
for reading RFID tags.
"""

from mfrc522 import SimpleMFRC522
import time
from threading import Event

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
    
    def read_tag(self):
        """
        Read an RFID tag and return its ID.
        
        Returns:
            tuple: (id, text) from the RFID tag
        """
        return self.reader.read()
    
    def read_tag_no_block(self):
        """
        Read an RFID tag without blocking if no tag is present.
        
        Returns:
            tuple: (id, text) from the RFID tag, or (None, None) if no tag
        """
        return self.reader.read_no_block()
    
    def read_with_timeout(self, timeout=None, check_interval=0.1):
        """
        Read an RFID tag with a timeout or until canceled.
        
        Args:
            timeout (float, optional): Maximum time to wait in seconds. None for no timeout.
            check_interval (float, optional): Time between read attempts in seconds.
            
        Returns:
            tuple: (id, text) or (None, None) if timeout/canceled
        """
        self.cancel_event.clear()
        start_time = time.time()
        
        while True:
            # Check for timeout
            if timeout and (time.time() - start_time > timeout):
                return None, None
                
            # Check for cancellation
            if self.cancel_event.is_set():
                return None, None
                
            # Try to read tag
            id_val, text = self.reader.read_no_block()
            if id_val is not None:
                return id_val, text
                
            time.sleep(check_interval)
    
    def cancel_read(self):
        """Cancel an ongoing read_with_timeout operation."""
        self.cancel_event.set()
