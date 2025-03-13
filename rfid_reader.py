"""
RFID reader functionality for the RFID Audio Player.

This module provides a wrapper around the SimpleMFRC522 library
for reading RFID tags.
"""

from mfrc522 import SimpleMFRC522
import time
import logging
from threading import Event, RLock

# Configure logging
logging.basicConfig(
    filename='/home/pi/rfid_audio.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('rfid_reader')

class RFIDReader:
    """
    A class to handle RFID tag reading operations.
    
    This class provides methods to read RFID tags and manage the
    active state of the reader.
    """
    
    def __init__(self):
        """Initialize the RFID reader."""
        self.reader = SimpleMFRC522()
        self.active_state = Event()
        self.active_state.set()  # Active by default
        self.cancel_event = Event()
        self.reader_lock = RLock()  # Add a lock for thread safety
        logger.info("RFID Reader initialized")
    
    def read_tag(self):
        """
        Read an RFID tag and return its ID.
        
        Returns:
            tuple: (id, text) from the RFID tag
        """
        with self.reader_lock:
            return self.reader.read()
    
    def read_tag_no_block(self):
        """
        Read an RFID tag without blocking if no tag is present.
        
        Returns:
            tuple: (id, text) from the RFID tag, or (None, None) if no tag
        """
        # Only attempt to read if active
        if not self.active_state.is_set():
            return None, None
            
        with self.reader_lock:
            try:
                return self.reader.read_no_block()
            except Exception as e:
                logger.error(f"Error reading RFID tag: {str(e)}")
                return None, None
    
    def read_with_timeout(self, timeout=10.0, check_interval=0.1):
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
        
        logger.info(f"Starting RFID read with timeout {timeout}s")
        
        while True:
            # Check for timeout
            if timeout is not None and (time.time() - start_time > timeout):
                logger.info("RFID read timed out")
                return None, None
                
            # Check for cancellation
            if self.cancel_event.is_set():
                logger.info("RFID read canceled")
                return None, None
            
            # Only attempt to read if active
            if not self.active_state.is_set():
                time.sleep(check_interval)
                continue
                
            # Try to read tag
            try:
                with self.reader_lock:
                    id_val, text = self.reader.read_no_block()
                if id_val is not None:
                    logger.info(f"RFID tag read: {id_val}")
                    return id_val, text
            except Exception as e:
                logger.error(f"Error during RFID read: {str(e)}")
                time.sleep(check_interval * 2)  # Longer delay after error
                
            time.sleep(check_interval)
    
    def cancel_read(self):
        """Cancel an ongoing read_with_timeout operation."""
        logger.info("RFID read operation canceled")
        self.cancel_event.set()
        
    def set_active(self, active=True):
        """
        Set the active state of the reader.
        
        Args:
            active (bool): Whether the reader should be active
        """
        if active:
            self.active_state.set()
            logger.info("RFID reader activated")
        else:
            self.active_state.clear()
            logger.info("RFID reader deactivated")
            
    def is_active(self):
        """
        Check if the reader is currently active.
        
        Returns:
            bool: True if active, False otherwise
        """
        return self.active_state.is_set()
        
    def close(self):
        """Clean up any resources."""
        logger.info("Closing RFID reader")
        self.cancel_read()
        self.set_active(False)
