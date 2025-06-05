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


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info(f"Received shutdown signal {sig}, initiating graceful shutdown...")
    shutdown_event.set()
    # Give some time for cleanup
    time.sleep(2)
    sys.exit(0)


def main():
    """Main application entry point with improved startup handling."""
    logger.info("Starting RFID Audio Player application")

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Initialize database
        logger.info("Initializing database")
        init_db()

        # Initialize components with error handling
        logger.info("Initializing application components")

        # Initialize audio player first (most likely to fail)
        try:
            audio_player = AudioPlayer()
        except Exception as e:
            logger.critical(f"Failed to initialize audio player: {e}")
            logger.info("Retrying audio player initialization in 5 seconds...")
            time.sleep(5)
            audio_player = AudioPlayer()

        # Initialize OLED menu
        try:
            oled_menu = OLEDMenu()
        except Exception as e:
            logger.critical(f"Failed to initialize OLED menu: {e}")
            raise

        # Initialize RFID reader
        try:
            rfid_reader = RFIDReader()
        except Exception as e:
            logger.critical(f"Failed to initialize RFID reader: {e}")
            raise

        # Start the RFID reader thread
        logger.info("Starting player thread")
        player_thread = th.Thread(
            target=audio_player.start_player,
            args=(rfid_reader, shutdown_event),
            daemon=True,
        )
        player_thread.start()

        # Show startup message on OLED
        oled_menu.display_message("RFID Audio Player\nStarted Successfully!")
        time.sleep(2)

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

                elif oled_menu.menu_selection == 3:  # Audio Settings
                    logger.debug("Entering Audio Settings menu")

                    # Initialize the menu state
                    oled_menu.current_menu = "audio_menu"
                    oled_menu.audio_menu_selection = 1  # Start with Volume selected
                    oled_menu.adjusting_volume = False

                    # Get current volume and output device
                    oled_menu.volume_value = audio_player.get_volume()
                    current_device = audio_player.get_current_audio_device()
                    oled_menu.audio_output_selection = (
                        0 if current_device == "speaker" else 1
                    )

                    # Menu interaction loop
                    oled_menu.option_confirmed = False
                    while (
                        not oled_menu.option_confirmed and not shutdown_event.is_set()
                    ):
                        # Display the menu
                        oled_menu.display_audio_menu()

                        # Wait for user input
                        time.sleep(0.1)

                        # Process user selection when confirmed
                        if oled_menu.option_confirmed:
                            logger.debug(
                                f"Audio menu option confirmed: {oled_menu.audio_menu_selection}"
                            )

                            if oled_menu.audio_menu_selection == 0:  # Back
                                # Exit the menu
                                logger.debug(
                                    "User selected Back, exiting Audio Settings"
                                )
                                break  # This will exit the while loop

                            elif oled_menu.audio_menu_selection == 1:  # Volume
                                # Toggle volume adjustment mode
                                oled_menu.adjusting_volume = (
                                    not oled_menu.adjusting_volume
                                )
                                logger.debug(
                                    f"Volume adjustment mode: {oled_menu.adjusting_volume}"
                                )

                                if not oled_menu.adjusting_volume:
                                    # Apply volume change when exiting adjustment mode
                                    audio_player.set_volume(oled_menu.volume_value)
                                    logger.info(
                                        f"Volume set to {oled_menu.volume_value}%"
                                    )

                                # Reset confirmation flag to stay in the menu
                                oled_menu.option_confirmed = False

                            elif oled_menu.audio_menu_selection == 2:  # Output Device
                                # Toggle between speaker and aux
                                oled_menu.audio_output_selection = (
                                    oled_menu.audio_output_selection + 1
                                ) % 2
                                new_device = (
                                    "speaker"
                                    if oled_menu.audio_output_selection == 0
                                    else "aux"
                                )
                                current_device = audio_player.get_current_audio_device()

                                if new_device != current_device:
                                    logger.info(
                                        f"Switching audio output from {current_device} to {new_device}"
                                    )
                                    oled_menu.display_message(
                                        f"Switching to {new_device.title()}..."
                                    )

                                    audio_player.stop()

                                    # Switch audio output
                                    success, error_msg = (
                                        audio_player.switch_audio_output(new_device)
                                    )

                                    if success:
                                        oled_menu.display_message(
                                            f"Switched to {new_device.title()}"
                                        )
                                    else:
                                        if "unavailable" in error_msg.lower():
                                            oled_menu.display_message(
                                                f"{new_device.title()} unavailable"
                                            )
                                        else:
                                            oled_menu.display_message(
                                                "Switch failed! Check logs"
                                            )

                                    time.sleep(1.5)

                                # Reset confirmation flag to stay in the menu
                                oled_menu.option_confirmed = False

                    # Reset to main menu
                    oled_menu.current_menu = "main"

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
