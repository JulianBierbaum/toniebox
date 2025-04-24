"""
RFID Audio Player for Raspberry Pi

A system to play audio files when specific RFID tags are detected,
with an OLED menu for configuration.

This is the main entry point for the application.
"""

import threading as th
import time
import signal
import sys

from models import init_db
from audio_player import AudioPlayer
from oled_menu import OLEDMenu
from rfid_reader import RFIDReader

# Global flag for graceful shutdown
running = True

def signal_handler(sig, frame):
    """Handle shutdown signals."""
    global running
    print("Shutting down...")
    running = False
    sys.exit(0)
    
def main():
    """Main application entry point."""
    # Set up signal handler for clean exits
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize database
    init_db()
    
    # Initialize components
    audio_player = AudioPlayer()
    oled_menu = OLEDMenu()
    rfid_reader = RFIDReader()
    
    # Start the RFID reader thread
    player_thread = th.Thread(
        target=audio_player.start_player,
        args=(rfid_reader,),
        daemon=True
    )
    player_thread.start()
    
    # Main UI loop
    try:
        while running:
            # Main menu display
            oled_menu.current_menu = "main"
            oled_menu.display_menu()
            oled_menu.wait_for_confirmation()
            
            if not running:
                break
                
            # Handle menu selection
            if oled_menu.menu_selection == 0:  # Currently Playing
                # Display current audio until confirm button is pressed
                oled_menu.option_confirmed = False
                while not oled_menu.option_confirmed and running:
                    current = audio_player.get_current_audio()
                    oled_menu.display_current_audio(current)
                    time.sleep(0.5)
                    
            elif oled_menu.menu_selection == 1:  # Add/Update Audio
                # Stop current playback and pause reader thread
                audio_player.stop()
                audio_player.reader_active = False
                
                try:
                    # Prompt for RFID tag
                    oled_menu.display_message("Hold RFID chip to reader")
                    
                    # Set up button handler to cancel read
                    original_confirm = oled_menu.confirm.when_pressed
                    oled_menu.confirm.when_pressed = rfid_reader.cancel_read
                    
                    # Try to read RFID tag with cancellation
                    id_val, _ = rfid_reader.read_with_timeout(timeout=30)
                    
                    # Restore original button handler
                    oled_menu.confirm.when_pressed = original_confirm
                    
                    if id_val is None:
                        continue
                    
                    # Check if tag is already mapped
                    existing = audio_player.get_file(str(id_val))
                    if existing:
                        oled_menu.display_message(f"Tag ID: {id_val}\nCurrent: {existing}")
                        time.sleep(2)
                        
                        oled_menu.current_menu = "yes_no"
                        oled_menu.display_yes_no_menu()
                        oled_menu.option_confirmed = False
                        
                        while not oled_menu.option_confirmed and running:
                            time.sleep(0.1)
                            
                        if oled_menu.yes_no_selection == 1:  # No
                            continue
                    
                    # Get list of audio files
                    files = audio_player.get_files_in_folder()
                    if not files:
                        oled_menu.display_message("No audio files found")
                        time.sleep(2)
                        continue
                    
                    # Display file selection menu
                    oled_menu.current_menu = "files"
                    oled_menu.file_options = files
                    oled_menu.file_selection = 0
                    oled_menu.display_file_menu(files)
                    oled_menu.option_confirmed = False
                    
                    while not oled_menu.option_confirmed and running:
                        time.sleep(0.1)
                    
                    if not running:
                        break
                    
                    # Save selection to database
                    selected_file = files[oled_menu.file_selection]
                    audio_player.add_file_to_db(str(id_val), selected_file)
                    
                    # Show confirmation
                    oled_menu.display_message(f"Added: {selected_file}\nID: {str(id_val)}")
                    time.sleep(2)
                    
                except Exception as e:
                    oled_menu.display_message(f"Error: {str(e)}")
                    time.sleep(2)
                finally:
                    # Always resume reader thread
                    audio_player.reader_active = True
                    
            elif oled_menu.menu_selection == 2:  # List Audios
                # Display list of audio files
                files = audio_player.get_files_in_folder()
                if files:
                    oled_menu.current_menu = "files"
                    oled_menu.file_options = files
                    oled_menu.file_selection = 0
                    oled_menu.option_confirmed = False
                    
                    while not oled_menu.option_confirmed and running:
                        oled_menu.display_file_menu(files)
                        time.sleep(0.1)
                    
                    if not running:
                        break
                    
                    # User confirmed file selection
                    selected_file = files[oled_menu.file_selection]
                    
                    # Stop playback and disable RFID reader
                    audio_player.stop()
                    audio_player.reader_active = False
                    
                    try:
                        # Play selected file
                        audio_player.play_file(selected_file)
                        
                        # Show currently playing screen until confirmation
                        oled_menu.option_confirmed = False
                        while not oled_menu.option_confirmed and running:
                            current = audio_player.get_current_audio()
                            oled_menu.display_current_audio(current)
                            time.sleep(0.5)
                    except Exception as e:
                        oled_menu.display_message(f"Playback error: {str(e)}")
                        time.sleep(2)
                    finally:
                        # Always stop playback and re-enable RFID when done
                        audio_player.stop()
                        audio_player.reader_active = True
                else:
                    oled_menu.display_message("No audio files")
                    time.sleep(2)
                    
    except KeyboardInterrupt:
        print("Application terminated by user")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
    finally:
        # Clean up resources
        audio_player.stop()
        # Signal to threads that we're shutting down
        running = False

if __name__ == "__main__":
    main()
