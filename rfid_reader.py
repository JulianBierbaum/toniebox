"""
RFID reader functionality for the RFID Audio Player.

This module provides a wrapper around the SimpleMFRC522 library
for reading RFID tags.
"""

from mfrc522 import SimpleMFRC522
import time
from threading import Event, Lock
import RPi.GPIO as GPIO

from logger import get_logger

logger = get_logger(__name__)

class RFIDReader:
    """
    A class to handle RFID tag reading operations.
    
    This class provides methods to read RFID tags and manage the
    active state of the reader.
    """
    
    def __init__(self):
        """Initialize the RFID reader."""
        logger.info("Initializing RFID reader")
        self.reader = SimpleMFRC522()
        self.active = True
        self.cancel_event = Event()
        self.reader_lock = Lock()
        self.consecutive_errors = 0
        self.max_consecutive_errors = 3
        self.last_successful_read_time = time.time()
        self.reinit_interval = 10
    
    def _reset_reader(self):
        """Reset the RFID reader hardware."""
        try:
            # Clean up GPIO
            GPIO.cleanup()
            # Reinitialize reader
            logger.info("Reinitializing RFID reader...")
            time.sleep(0.5)  # Give hardware time to reset
            self.reader = SimpleMFRC522()
        except Exception as e:
            logger.error(f"Error resetting RFID reader: {e}")
    
    def _handle_read_error(self, error, operation="read"):
        """
        Centralized error handling for RFID read operations
        
        Args:
            error: The exception that occurred
            operation: String describing the operation that failed
            
        Returns:
            tuple: (None, None) as default error return value
        """
        logger.error(f"RFID {operation} error: {error}")
        self.consecutive_errors += 1
        
        # If we get too many consecutive errors, reset the reader
        if self.consecutive_errors >= self.max_consecutive_errors:
            logger.warning(f"Too many consecutive errors ({self.consecutive_errors}), resetting reader")
            self._reset_reader()
            self.consecutive_errors = 0
            
        return None, None
    
    def _update_success_metrics(self, id_val):
        """Update tracking metrics on successful read"""
        if id_val is not None:
            logger.debug(f"Read successful: {id_val}")
            self.consecutive_errors = 0
            self.last_successful_read_time = time.time()
    
    def read_tag(self):
        """
        Read an RFID tag and return its ID.
        
        Returns:
            tuple: (id, text) from the RFID tag
        """
        with self.reader_lock:
            try:
                id_val, text = self.reader.read()
                self._update_success_metrics(id_val)
                return id_val, text
            except Exception as e:
                return self._handle_read_error(e)
    
    def read_tag_no_block(self):
        """
        Read an RFID tag without blocking if no tag is present.
        
        Returns:
            tuple: (id, text) from the RFID tag, or (None, None) if no tag
        """
        # Check if we need a proactive reset
        if time.time() - self.last_successful_read_time > self.reinit_interval:
            logger.info("No successful reads for a while, proactively reinitializing reader...")
            self._reset_reader()
            self.last_successful_read_time = time.time()
            
        with self.reader_lock:
            try:
                id_val, text = self.reader.read_no_block()
                self._update_success_metrics(id_val)
                return id_val, text
            except Exception as e:
                return self._handle_read_error(e, "read_no_block")
    
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
        logger.info(f"Starting RFID read with {timeout}s timeout")
        self.cancel_event.clear()
        start_time = time.time()
        retries = 0

        while True:
            # Check for timeout
            if timeout and (time.time() - start_time > timeout):
                logger.info("RFID read timeout")
                return None, None
                
            # Check for cancellation
            if self.cancel_event.is_set():
                logger.info("RFID read cancelled")
                return None, None

            with self.reader_lock:
                try:
                    # Try to read tag
                    id_val, text = self.reader.read_no_block()
                    if id_val is not None:
                        self._update_success_metrics(id_val)
                        return id_val, text
                except Exception as e:
                    logger.error(f"RFID read error: {e}")
                    retries += 1
                    if retries > max_retries:
                        logger.warning("Max retries reached, giving up.")
                        # Reset the reader before giving up
                        self._reset_reader()
                        return None, None
                    
                    # Reinitialize reader
                    self._reset_reader()
            
            time.sleep(check_interval)
    
    def cancel_read(self):
        """Cancel an ongoing read_with_timeout operation."""
        logger.info("Cancelling RFID read")
        self.cancel_event.set()
