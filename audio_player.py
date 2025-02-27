"""
Audio playback functionality for the RFID Audio Player.

This module handles audio file playback and management of audio files
associated with RFID tags.
"""

import pygame as pg
import threading as th
import time
import os
from threading import Lock, Event

from models import Session, RFIDAudio

class AudioPlayer:
    """
    A class to handle audio playback and RFID-to-audio mapping.
    
    This class provides methods to play, stop, and manage audio files
    associated with RFID tags.
    """
    
    def __init__(self, media_path="/media/pi"):
        """
        Initialize the audio player.
        
        Args:
            media_path (str): Path to the directory containing audio files
        """
        pg.mixer.init()
        self.session = Session()
        self.current_audio_lock = Lock()
        self.current_audio = None
        self.playback_event = Event()
        self.reader_active = True
        self.media_path = media_path
        
        # Initialize database with a sample record if empty
        self._init_default_record()
    
    def _init_default_record(self):
        """Initialize the database with a default record if it's empty."""
        if not self.session.query(RFIDAudio).first():
            record = RFIDAudio(id="631430949643", file="outro.mp3")
            self.session.add(record)
            self.session.commit()
    
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
            return

        with self.current_audio_lock:
            self.current_audio = audio_file
            
        # Stop any currently playing audio
        if hasattr(self, 'audio_thread') and self.audio_thread.is_alive():
            self.playback_event.set()
            self.audio_thread.join()
            
        # Start new audio playback
        self.playback_event.clear()
        self.audio_thread = th.Thread(target=self._play_audio, args=(audio_file,))
        self.audio_thread.daemon = True  # Make thread daemon so it exits when main program exits
        self.audio_thread.start()

    def _play_audio(self, audio_file):
        """
        Internal method to play audio in a separate thread.
        
        Args:
            audio_file (str): The audio file to play
        """
        try:
            full_path = os.path.join(self.media_path, audio_file)
            pg.mixer.music.load(full_path)
            pg.mixer.music.play()
            
            # Keep thread alive until playback finishes or is interrupted
            while pg.mixer.music.get_busy() and not self.playback_event.is_set():
                pg.time.Clock().tick(10)
                
        except Exception as e:
            print(f"Audio playback error: {str(e)}")
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

    def get_file(self, file_id):
        """
        Get the audio filename associated with an RFID ID.
        
        Args:
            file_id (str): The RFID tag ID to look up
            
        Returns:
            str or None: The associated audio filename or None if not found
        """
        record = self.session.query(RFIDAudio).filter_by(id=file_id).first()
        return record.file if record else None
    
    def get_files_in_folder(self):
        """
        Get a list of all audio files in the media directory.
        
        Returns:
            list: A list of filenames in the media directory
        """
        folder_path = self.media_path
        if not os.path.exists(folder_path):
            return []
            
        return [file for file in os.listdir(folder_path) 
                if os.path.isfile(os.path.join(folder_path, file))]

    def add_file_to_db(self, file_id, file_name):
        """
        Associate an audio file with an RFID ID in the database.
        
        Args:
            file_id (str): The RFID tag ID
            file_name (str): The audio filename to associate with the ID
        """
        record = self.session.query(RFIDAudio).filter_by(id=file_id).first()
        if record:
            record.file = file_name
        else:
            record = RFIDAudio(id=file_id, file=file_name)
            self.session.add(record)
        self.session.commit()

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
        
        while True:
            if not self.reader_active:
                time.sleep(0.1)
                continue

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
            
            time.sleep(0.1)

    def __del__(self):
        """Clean up resources when object is destroyed."""
        try:
            pg.mixer.quit()
        except:
            pass
            
        try:
            self.session.close()
        except:
            pass
