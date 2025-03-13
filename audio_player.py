"""
Audio playback functionality for the RFID Audio Player.

This module handles audio file playback and management of audio files
associated with RFID tags.
"""

import pygame as pg
import threading as th
import time
import os
import logging
from threading import Lock, Event

from models import Session, RFIDAudio

# Configure logging
logging.basicConfig(
    filename='/home/pi/rfid_audio.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('audio_player')

class AudioPlayer:
    """
    A class to handle audio playback and RFID-to-audio mapping.
    
    This class provides methods to play, stop, and manage audio files
    associated with RFID tags.
    """
    
    def __init__(self, media_path="/media/pi", sample_rate=44100, buffer=4096):
        """
        Initialize the audio player.
        
        Args:
            media_path (str): Path to the directory containing audio files
            sample_rate (int): Audio sample rate to use for pygame mixer
            buffer (int): Buffer size for pygame mixer
        """
        # Initialize pygame mixer with specific parameters for better performance
        pg.mixer.init(frequency=sample_rate, buffer=buffer)
        self.session = Session()
        self.current_audio_lock = Lock()
        self.current_audio = None
        self.playback_event = Event()
        self.stop_event = Event()  # Event to signal threads to stop
        self.media_path = media_path
        
        # Initialize database with a sample record if empty
        self._init_default_record()
        
        logger.info("AudioPlayer initialized with media path: %s", media_path)
    
    def _init_default_record(self):
        """Initialize the database with a default record if it's empty."""
        try:
            if not self.session.query(RFIDAudio).first():
                record = RFIDAudio(id="631430949643", file="outro.mp3")
                self.session.add(record)
                self.session.commit()
                logger.info("Added default record to database")
        except Exception as e:
            logger.error("Failed to initialize default record: %s", str(e))
            # Rollback the session if an error occurs
            self.session.rollback()
    
    def play(self, file_id):
        """
        Play audio associated with the given RFID ID.
        
        Args:
            file_id (str): The RFID tag ID to play audio for
        """
        audio_file = self.get_file(file_id)
        if not audio_file:
            with self.current_audio_lock:
                self.current_audio = f"Unknown ID: {file_id}"
            logger.warning("Unknown RFID ID: %s", file_id)
            return

        with self.current_audio_lock:
            self.current_audio = audio_file
            
        # Stop any currently playing audio
        self.stop_current_audio()
            
        # Start new audio playback
        self.playback_event.clear()
        self.audio_thread = th.Thread(target=self._play_audio, args=(audio_file,))
        self.audio_thread.daemon = True  # Make thread daemon so it exits when main program exits
        self.audio_thread.start()
        logger.info("Started playback of %s for ID %s", audio_file, file_id)

    def stop_current_audio(self):
        """Stop any currently playing audio and wait for the thread to end."""
        if hasattr(self, 'audio_thread') and self.audio_thread.is_alive():
            self.playback_event.set()
            self.audio_thread.join(timeout=1.0)  # Wait with timeout to avoid blocking indefinitely
            if self.audio_thread.is_alive():
                logger.warning("Audio thread did not terminate properly")

    def _play_audio(self, audio_file):
        """
        Internal method to play audio in a separate thread.
        
        Args:
            audio_file (str): The audio file to play
        """
        try:
            full_path = os.path.join(self.media_path, audio_file)
            if not os.path.exists(full_path):
                logger.error("Audio file not found: %s", full_path)
                with self.current_audio_lock:
                    self.current_audio = f"File not found: {audio_file}"
                return
                
            pg.mixer.music.load(full_path)
            pg.mixer.music.play()
            logger.debug("Playing audio file: %s", full_path)
            
            # Keep thread alive until playback finishes or is interrupted
            while pg.mixer.music.get_busy() and not self.playback_event.is_set():
                pg.time.Clock().tick(10)
                
        except Exception as e:
            logger.error("Audio playback error: %s", str(e))
        finally:
            with self.current_audio_lock:
                if self.current_audio == audio_file:
                    self.current_audio = None

    def stop(self):
        """Stop any currently playing audio."""
        self.playback_event.set()
        pg.mixer.music.stop()
        with self.current_audio_lock:
            self.current_audio = None
        logger.debug("Stopped audio playback")

    def get_file(self, file_id):
        """
        Get the audio filename associated with an RFID ID.
        
        Args:
            file_id (str): The RFID tag ID to look up
            
        Returns:
            str or None: The associated audio filename or None if not found
        """
        try:
            record = self.session.query(RFIDAudio).filter_by(id=file_id).first()
            return record.file if record else None
        except Exception as e:
            logger.error("Database query error: %s", str(e))
            # Refresh the session to avoid stale data
            self.session.rollback()
            self._refresh_session()
            return None
    
    def get_files_in_folder(self):
        """
        Get a list of all audio files in the media directory.
        
        Returns:
            list: A list of filenames in the media directory
        """
        folder_path = self.media_path
        if not os.path.exists(folder_path):
            logger.warning("Media directory does not exist: %s", folder_path)
            return []
            
        try:
            # Filter for common audio file extensions
            audio_extensions = ('.mp3', '.wav', '.ogg', '.flac')
            files = [file for file in os.listdir(folder_path) 
                    if os.path.isfile(os.path.join(folder_path, file)) and 
                    file.lower().endswith(audio_extensions)]
            return files
        except Exception as e:
            logger.error("Error listing files in directory: %s", str(e))
            return []

    def add_file_to_db(self, file_id, file_name):
        """
        Associate an audio file with an RFID ID in the database.
        
        Args:
            file_id (str): The RFID tag ID
            file_name (str): The audio filename to associate with the ID
        """
        try:
            record = self.session.query(RFIDAudio).filter_by(id=file_id).first()
            if record:
                record.file = file_name
            else:
                record = RFIDAudio(id=file_id, file=file_name)
                self.session.add(record)
            self.session.commit()
            logger.info("Added/updated database record: ID %s -> %s", file_id, file_name)
        except Exception as e:
            logger.error("Database update error: %s", str(e))
            self.session.rollback()
            self._refresh_session()

    def get_current_audio(self):
        """
        Get the currently playing audio filename.
        
        Returns:
            str or None: The currently playing audio filename or None
        """
        with self.current_audio_lock:
            return self.current_audio

    def start_player(self, rfid_reader):
        """
        Start continuously reading RFID tags and playing associated audio.
        
        Args:
            rfid_reader: An instance of RFIDReader to use for tag reading
        """
        current_id = 0
        none_counter = 0
        
        logger.info("Starting RFID reader loop")
        
        while not self.stop_event.is_set():
            if not rfid_reader.is_active():
                time.sleep(0.1)
                continue

            try:
                id_val, text = rfid_reader.read_tag_no_block()
                if id_val is not None:
                    if id_val != current_id:
                        current_id = id_val
                        self.play(str(id_val))
                        time.sleep(2)  # Debounce time
                
                if id_val is None:
                    none_counter += 1
                else:
                    none_counter = 0
                
                # Stop playback if tag is removed (multiple empty reads)
                if none_counter >= 2:
                    self.stop()
                    none_counter = 0
                    current_id = 0
            except Exception as e:
                logger.error("Error in RFID reader loop: %s", str(e))
                time.sleep(0.5)  # Pause briefly to avoid rapid error loop
            
            time.sleep(0.1)
            
        logger.info("RFID reader loop stopped")

    def _refresh_session(self):
        """Refresh the database session."""
        try:
            self.session.close()
            self.session = Session()
        except Exception as e:
            logger.error("Failed to refresh database session: %s", str(e))

    def close(self):
        """Properly close all resources."""
        logger.info("Closing AudioPlayer resources")
        self.stop_event.set()  # Signal all threads to stop
        self.stop()  # Stop audio playback
        
        try:
            pg.mixer.quit()
        except Exception as e:
            logger.error("Error closing pygame mixer: %s", str(e))
            
        try:
            self.session.close()
        except Exception as e:
            logger.error("Error closing database session: %s", str(e))
