"""
Audio playback functionality for the RFID Audio Player.

This module handles audio file playback and management of audio files
associated with RFID tags.
"""

import os
import threading as th
import time
from threading import Event, Lock
from dotenv import load_dotenv

import pygame as pg

from .logger import get_logger
from .model import RFIDAudio, Session

logger = get_logger(__name__)

load_dotenv()


class AudioPlayer:
    """
    A class to handle audio playback and RFID-to-audio mapping.

    This class provides methods to play, stop, and manage audio files
    associated with RFID tags.
    """

    def __init__(self, media_path=os.getenv("MEDIA_PATH")):
        """
        Initialize the audio player.

        Args:
            media_path (str): Path to the directory containing audio files
        """
        logger.info("Initializing AudioPlayer")

        self.current_output_device = os.getenv("DEFAULT_AUDIO_DEVICE", "speaker")
        self._initialize_audio(self.current_output_device)

        self.session = Session()
        self.audio_lock = Lock()
        self.current_audio = None
        self.playback_event = Event()
        self.reader_active = True
        self.media_path = media_path
        self.audio_thread = None

        # Initialize volume to default value
        default_volume = int(os.getenv("DEFAULT_VOLUME", "25"))
        self.current_volume = default_volume
        self.set_volume(default_volume)
        logger.info(f"Volume initialized to {default_volume}%")

    def _initialize_audio(self, device):
        """
        Internal helper to set environment and initialize mixer.
        Falls back if specified device is unavailable.

        Args:
            device (str): 'speaker' or 'aux'

        Returns:
            bool: True if initialization successful, False otherwise
        """
        logger.info(f"Initializing audio for device: {device}")

        try:
            if pg.mixer.get_init():
                pg.mixer.quit()
        except Exception:
            pass

        def try_device(dev_name, alsa_hw):
            os.environ["SDL_AUDIODRIVER"] = "alsa"
            os.environ["AUDIODEV"] = alsa_hw
            try:
                pg.mixer.init()
                logger.info(f"Audio initialized successfully on device: {dev_name}")
                return True
            except Exception as e:
                logger.warning(f"Failed to initialize audio on {dev_name}: {str(e)}")
                return False

        # Try to initialize the requested device without falling back
        if device == "aux":
            success = try_device("aux", "hw:0,0")
            if success:
                self.current_output_device = "aux"
            return success
        else:  # device == "speaker"
            success = try_device("speaker", "hw:1,0")
            if success:
                self.current_output_device = "speaker"
            return success

    def play_file(self, filename):
        """Play an audio file directly by filename"""
        logger.info(f"Playing file: {filename}")
        self._play_audio_track(filename)

    def play(self, file_id):
        """
        Play audio associated with the given RFID ID.

        Args:
            file_id (int): The RFID tag ID to play audio for
        """
        audio_file = self.get_file(file_id)
        if not audio_file:
            logger.warning(f"Unknown RFID ID: {file_id}")
            with self.audio_lock:
                self.current_audio = f"Unknown ID: {file_id}"
            return

        logger.info(f"Playing audio for RFID ID: {file_id}, file: {audio_file}")
        self._play_audio_track(audio_file)

    def _play_audio_track(self, audio_file):
        """
        Unified method to handle both direct file playback and RFID-triggered playback.

        Args:
            audio_file (str): The audio file to play
        """
        with self.audio_lock:
            # Stop any currently playing audio
            self.stop()

            # Update current audio info
            self.current_audio = audio_file

            # Start new audio playback
            self.playback_event.clear()
            self.audio_thread = th.Thread(target=self._play_audio, args=(audio_file,))
            self.audio_thread.daemon = (
                True  # Make thread daemon so it exits when main program exits
            )
            self.audio_thread.start()

    def _play_audio(self, audio_file):
        """
        Internal method to play audio in a separate thread.

        Args:
            audio_file (str): The audio file to play
        """
        try:
            full_path = os.path.join(self.media_path, audio_file)

            # Check if file exists before trying to play it
            if not os.path.exists(full_path):
                logger.error(f"Audio file not found: {full_path}")
                with self.audio_lock:
                    self.current_audio = f"File not found: {audio_file}"
                return

            pg.mixer.music.load(full_path)
            pg.mixer.music.play()
            logger.debug(f"Started playback of: {audio_file}")

            # Keep thread alive until playback finishes or is interrupted
            while pg.mixer.music.get_busy() and not self.playback_event.is_set():
                pg.time.Clock().tick(10)

        except Exception as e:
            logger.error(f"Audio playback error: {str(e)}")
        finally:
            # Only clear current_audio if it hasn't been changed
            with self.audio_lock:
                if self.current_audio == audio_file:
                    self.current_audio = None
            logger.debug(f"Playback finished or stopped: {audio_file}")

    def stop(self):
        """Stop any currently playing audio."""
        # Set the event to signal thread to stop
        self.playback_event.set()

        # Stop pygame playback
        try:
            pg.mixer.music.stop()
            logger.debug("Stopped audio playback")
        except Exception as e:
            logger.debug(f"Error stopping playback: {str(e)}")

        # Wait for thread to finish if it exists and is alive
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=1.0)  # Wait with timeout

    def get_file(self, file_id):
        """
        Get the audio filename associated with an RFID ID.

        Args:
            file_id (int): The RFID tag ID to look up

        Returns:
            str or None: The associated audio filename or None if not found
        """
        # Create a new session for thread safety
        session = Session()
        try:
            record = session.query(RFIDAudio).filter_by(id=file_id).first()
            return record.file if record else None
        finally:
            session.close()

    def get_files_in_folder(self):
        """
        Get a list of all audio files in the media directory.

        Returns:
            list: A list of filenames in the media directory
        """
        folder_path = self.media_path
        if not os.path.exists(folder_path):
            logger.warning(f"Media directory not found: {folder_path}")
            return []

        files = [
            file
            for file in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, file))
        ]
        logger.debug(f"Found {len(files)} files in {folder_path}")
        return files

    def add_file_to_db(self, file_id, file_name):
        """
        Associate an audio file with an RFID ID in the database.

        Args:
            file_id (int): The RFID tag ID
            file_name (str): The audio filename to associate with the ID
        """
        session = Session()
        try:
            record = session.query(RFIDAudio).filter_by(id=file_id).first()
            if record:
                logger.info(
                    f"Updating RFID mapping: ID {file_id} from {record.file} to {file_name}"
                )
                record.file = file_name
            else:
                logger.info(f"Adding new RFID mapping: ID {file_id} to {file_name}")
                record = RFIDAudio(id=file_id, file=file_name)
                session.add(record)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_current_audio(self):
        """
        Get the currently playing audio filename.

        Returns:
            str or None: The currently playing audio filename or None
        """
        with self.audio_lock:
            return self.current_audio

    def switch_audio_output(self, output_device):
        """
        Switch audio output between different devices.

        Args:
            output_device (str): 'speaker' for external speaker or 'aux' for aux port

        Returns:
            tuple: (bool, str) - Success flag and error message if applicable
        """
        logger.info(f"Switching audio output to: {output_device}")
        try:
            self.stop()

            # First try initializing the requested device
            success = self._initialize_audio(output_device)

            if success:
                self.current_output_device = output_device
                # Re-apply volume after switching devices
                self.set_volume(self.current_volume)
                return True, ""
            else:
                error_msg = f"{output_device.title()} device unavailable"
                logger.error(f"Failed to switch to {output_device}: {error_msg}")
                return False, error_msg

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error switching audio output: {error_msg}")
            return False, error_msg

    def get_current_audio_device(self):
        """
        Get the name of the currently active output device.

        Returns:
            str: 'speaker' or 'aux'
        """
        return getattr(self, "current_output_device", "speaker")

    def set_volume(self, volume_percent):
        """
        Set the playback volume level.

        Args:
            volume_percent (int): Volume level from 0-100

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            volume_percent = max(0, min(100, volume_percent))
            volume = volume_percent / 100.0

            pg.mixer.music.set_volume(volume)

            self.current_volume = volume_percent
            logger.debug(f"Volume set to {volume_percent}%")

            return True
        except Exception as e:
            logger.error(f"Error setting volume: {str(e)}")
            return False

    def get_volume(self):
        """
        Get the current volume level.

        Returns:
            int: Volume level from 0-100
        """
        # Return stored volume or get from pygame if available
        if hasattr(self, "current_volume"):
            return self.current_volume
        else:
            try:
                # Get from pygame and convert to percentage
                vol = pg.mixer.music.get_volume() * 100
                self.current_volume = int(vol)
                return self.current_volume
            except Exception:
                # Default if unable to get volume
                default_volume = int(os.getenv("DEFAULT_VOLUME", "25"))
                self.current_volume = default_volume
                return self.current_volume

    def start_player(self, rfid_reader, shutdown_event):
        """
        Start continuously reading RFID tags and playing associated audio.

        Args:
            rfid_reader: An instance of RFIDReader to use for tag reading
            shutdown_event: Event to monitor for shutdown signals
        """
        logger.info("Starting RFID player loop")
        current_id = 0
        none_counter = 0

        while not shutdown_event.is_set():
            if not self.reader_active:
                time.sleep(0.1)
                continue

            try:
                id_val, text = rfid_reader.read_tag_no_block()
                if id_val is not None:
                    if id_val != current_id:
                        current_id = id_val
                        logger.info(f"New RFID tag detected: {id_val}")
                        self.play(id_val)
                        time.sleep(2)  # Debounce time

                if id_val is None:
                    none_counter += 1
                else:
                    none_counter = 0

                # Stop playback if tag is removed (multiple empty reads)
                if none_counter >= 2:
                    logger.debug(f"RFID tag removed: {current_id}")
                    self.stop()
                    none_counter = 0
                    current_id = 0
            except Exception as e:
                logger.error(f"Error in RFID reading loop: {str(e)}")
                # Reset counters on error
                none_counter = 0
                current_id = 0
                time.sleep(1)

            time.sleep(0.1)

    def __del__(self):
        """Clean up resources when object is destroyed."""
        logger.debug("Cleaning up AudioPlayer resources")
        try:
            self.stop()
            pg.mixer.quit()
        except Exception as e:
            logger.debug(f"Error during cleanup: {str(e)}")

        try:
            self.session.close()
        except Exception as e:
            logger.debug(f"Error closing session: {str(e)}")
