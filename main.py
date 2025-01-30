import pygame as pg
import threading as th
from mfrc522 import SimpleMFRC522
from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import time
import os
from threading import Lock, Event
from gpiozero import Button
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106
from PIL import ImageFont

from menu import OLEDMenu
from audio import Audio
from rfidaudio import RFIDAudio
print("Hello BJ!")
# Database setup remains the same
Base = declarative_base()
DATABASE_URL = "sqlite:///rfid_audio.db"



engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)



def main():
    print("Hello Main!")
    audio = Audio()  # Your existing Audio class
    oled_menu = OLEDMenu()
    print("Hello Main2!")
    # Start the RFID reader thread
    player_thread = th.Thread(target=audio.start_player, daemon=True)
    player_thread.start()
    reader = SimpleMFRC522()

    while True:
        print("Hello BJ2!")
        oled_menu.current_menu = "main"
        oled_menu.display_menu()
        oled_menu.option_confirmed = False

        while not oled_menu.option_confirmed:
            time.sleep(0.1)

        if oled_menu.menu_selection == 0:  # Currently Playing
            oled_menu.option_confirmed = False
            while not oled_menu.option_confirmed:
                current = audio.get_current_audio()
                oled_menu.display_current_audio(current)
                time.sleep(0.5)

        elif oled_menu.menu_selection == 1:  # Add/Update Audio
            audio.stop()
            audio.reader_active = False
            
            try:
                oled_menu.display_message("Hold RFID chip to reader")
                # Set up a cancellation flag
                read_cancelled = False
                
                def cancel_read():
                    nonlocal read_cancelled
                    read_cancelled = True
                
                # Temporarily reassign button handlers for cancellation
                oled_menu.up.when_pressed = cancel_read
                oled_menu.down.when_pressed = cancel_read
                oled_menu.confirm.when_pressed = cancel_read
                
                # Try to read RFID with timeout checks
                id = None
                while not read_cancelled and id is None:
                    id, text = reader.read_no_block()
                    time.sleep(0.1)
                
                # Restore original button handlers
                oled_menu.up.when_pressed = oled_menu.on_up_pressed
                oled_menu.down.when_pressed = oled_menu.on_down_pressed
                oled_menu.confirm.when_pressed = oled_menu.on_confirm_pressed
                
                if read_cancelled or id is None:
                    continue
                
                existing = audio.session.query(RFIDAudio).filter_by(id=str(id)).first()
                if existing:
                    oled_menu.current_menu = "yes_no"
                    oled_menu.display_yes_no_menu()
                    oled_menu.option_confirmed = False
                    
                    while not oled_menu.option_confirmed:
                        time.sleep(0.1)
                        
                    if oled_menu.yes_no_selection == 1:  # No
                        continue

                files = audio.get_files_in_folder()
                if not files:
                    oled_menu.display_message("No audio files found")
                    time.sleep(2)
                    continue
                
                oled_menu.current_menu = "files"
                oled_menu.file_options = files
                oled_menu.display_file_menu(files)
                oled_menu.option_confirmed = False

                while not oled_menu.option_confirmed:
                    time.sleep(0.1)

                selected_file = files[oled_menu.file_selection]
                audio.add_file_to_db(str(id), selected_file)
                oled_menu.display_message(f"Added: {selected_file}\nID: {str(id)}")
                time.sleep(2)

            except Exception as e:
                oled_menu.display_message(f"Error: {str(e)}")
                time.sleep(2)
            finally:
                audio.reader_active = True

        elif oled_menu.menu_selection == 2:  # List Audios
            files = audio.get_files_in_folder()
            if files:
                oled_menu.current_menu = "files"
                oled_menu.file_options = files
                oled_menu.option_confirmed = False
                while not oled_menu.option_confirmed:
                    oled_menu.display_file_menu(files)
                    time.sleep(0.1)
            else:
                oled_menu.display_message("No audio files")
                time.sleep(2)

if __name__ == "__main__":
    main()
