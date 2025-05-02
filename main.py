"""
RFID Audio Player for Raspberry Pi

A system to play audio files when specific RFID tags are detected,
with an OLED menu for configuration.

This is the main entry point for the application.
"""

import signal
import sys
import threading as th
import time

from audio_player import AudioPlayer
from logger import get_logger
from model import init_db
from oled_menu import OLEDMenu
from rfid_reader import RFIDReader

# Initialize logger
logger = get_logger(__name__)

shutdown_event = th.Event()


def signal_handler():
    """Handle shutdown signals."""
    logger.info("Received shutdown signal, initiating graceful shutdown...")
    shutdown_event.set()
    sys.exit(0)


def main():
    """Main application entry point."""
    logger.info("Starting RFID Audio Player application")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Initialize database
        logger.info("Initializing database")
        init_db()

        # Initialize components
        logger.info("Initializing application components")
        audio_player = AudioPlayer()
        oled_menu = OLEDMenu()
        rfid_reader = RFIDReader()

        # Start the RFID reader thread
        logger.info("Starting player thread")
        player_thread = th.Thread(
            target=audio_player.start_player,
            args=(rfid_reader, shutdown_event),
            daemon=True,
        )
        player_thread.start()

        # Main UI loop
        logger.debug("Entering main UI loop")
        try:
            while not shutdown_event.is_set():
                # Main menu display
                oled_menu.current_menu = "main"
                oled_menu.display_menu()
                oled_menu.wait_for_confirmation()

                if shutdown_event.is_set():
                    logger.debug("Shutdown detected in UI loop")
                    break

                logger.debug(f"Menu selection: {oled_menu.menu_selection}")

                if oled_menu.menu_selection == 0:  # Currently Playing
                    logger.debug("Entering Currently Playing menu")
                    oled_menu.option_confirmed = False
                    oled_menu.current_menu = "currently_playing"
                    while (
                        not oled_menu.option_confirmed and not shutdown_event.is_set()
                    ):
                        current = audio_player.get_current_audio()
                        oled_menu.display_current_audio(current)
                        time.sleep(0.5)
                    oled_menu.current_menu = "main"

                elif oled_menu.menu_selection == 1:  # Add/Update Audio
                    logger.info("Entering Add/Update Audio menu")
                    audio_player.stop()
                    audio_player.reader_active = False
                    oled_menu.current_menu = "add_update"

                    try:
                        oled_menu.display_message("Hold RFID chip to reader")
                        logger.debug("Waiting for RFID tag registration")

                        original_confirm = oled_menu.confirm.when_pressed
                        oled_menu.confirm.when_pressed = rfid_reader.cancel_read

                        logger.debug("Starting RFID read with timeout")
                        id_val, _ = rfid_reader.read_with_timeout(timeout=30)

                        oled_menu.confirm.when_pressed = original_confirm

                        if id_val is None:
                            logger.debug("RFID read timed out or was cancelled")
                            continue

                        logger.info(f"Detected RFID tag: {id_val}")
                        existing = audio_player.get_file(str(id_val))
                        if existing:
                            oled_menu.display_message(
                                f"Tag ID: {id_val}\nCurrent: {existing}"
                            )
                            logger.debug(
                                f"Existing mapping found for tag {id_val}: {existing}"
                            )
                            time.sleep(2)

                            oled_menu.current_menu = "yes_no"
                            oled_menu.display_yes_no_menu()
                            oled_menu.option_confirmed = False

                            while (
                                not oled_menu.option_confirmed
                                and not shutdown_event.is_set()
                            ):
                                time.sleep(0.1)

                            if oled_menu.yes_no_selection == 1:  # No
                                logger.debug("User cancelled update")
                                continue

                        files = audio_player.get_files_in_folder()
                        if not files:
                            logger.warning("No audio files found in directory")
                            oled_menu.display_message("No audio files found")
                            time.sleep(2)
                            continue

                        logger.debug("Displaying file selection menu")
                        oled_menu.current_menu = "files"
                        oled_menu.file_options = files
                        oled_menu.file_selection = 0
                        oled_menu.display_file_menu(files)
                        oled_menu.option_confirmed = False

                        while (
                            not oled_menu.option_confirmed
                            and not shutdown_event.is_set()
                        ):
                            time.sleep(0.1)

                        if shutdown_event.is_set():
                            break

                        selected_file = files[oled_menu.file_selection]
                        logger.info(f"Mapping tag {id_val} to file {selected_file}")
                        audio_player.add_file_to_db(str(id_val), selected_file)

                        oled_menu.display_message(
                            f"Added: {selected_file}\nID: {str(id_val)}"
                        )
                        time.sleep(2)

                    except Exception as e:
                        logger.error(f"Error in Add/Update Audio menu: {str(e)}")
                        oled_menu.display_message(f"Error: {str(e)}")
                        time.sleep(2)
                    finally:
                        logger.debug("Resetting reader active state")
                        audio_player.reader_active = True
                        oled_menu.current_menu = "main"

                elif oled_menu.menu_selection == 2:  # List Audios
                    logger.debug("Entering List Audios menu")
                    files = audio_player.get_files_in_folder()
                    if files:
                        logger.debug(f"Found {len(files)} audio files")
                        oled_menu.current_menu = "files"
                        oled_menu.file_options = files
                        oled_menu.file_selection = 0
                        oled_menu.option_confirmed = False

                        while (
                            not oled_menu.option_confirmed
                            and not shutdown_event.is_set()
                        ):
                            oled_menu.display_file_menu(files)
                            time.sleep(0.1)

                        if shutdown_event.is_set():
                            break

                        selected_file = files[oled_menu.file_selection]
                        logger.info(f"Selected file for playback: {selected_file}")
                        audio_player.stop()
                        audio_player.reader_active = False

                        try:
                            logger.debug("Starting file playback")
                            audio_player.play_file(selected_file)
                            oled_menu.option_confirmed = False
                            while (
                                not oled_menu.option_confirmed
                                and not shutdown_event.is_set()
                            ):
                                current = audio_player.get_current_audio()
                                oled_menu.display_current_audio(current)
                                time.sleep(0.5)
                        except Exception as e:
                            logger.error(f"Playback error: {str(e)}")
                            oled_menu.display_message(f"Playback error: {str(e)}")
                            time.sleep(2)
                        finally:
                            logger.debug("Stopping playback and resetting reader")
                            audio_player.stop()
                            audio_player.reader_active = True
                    else:
                        logger.debug("No audio files available")
                        oled_menu.display_message("No audio files")
                        time.sleep(2)

        except KeyboardInterrupt:
            logger.info("Application terminated by user via keyboard")
        except Exception as e:
            logger.critical(f"Unexpected error in main loop: {str(e)}", exc_info=True)
        finally:
            logger.info("Cleaning up resources")
            audio_player.stop()
            shutdown_event.set()

    except Exception as e:
        logger.critical(f"Fatal initialization error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
