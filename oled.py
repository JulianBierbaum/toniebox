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

# Database setup remains the same
Base = declarative_base()
DATABASE_URL = "sqlite:///rfid_audio.db"

class RFIDAudio(Base):
    __tablename__ = "rfid_audio"
    id = Column(String, primary_key=True)
    file = Column(String, nullable=False)

engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

class Audio:
    def __init__(self):
        pg.mixer.init()
        self.session = Session()
        self.current_audio_lock = Lock()
        self.current_audio = None
        self.playback_event = Event()
        self.reader_active = True
        
        if not self.session.query(RFIDAudio).first():
            record = RFIDAudio(id="631430949643", file="outro.mp3")
            self.session.add(record)
            self.session.commit()

    def play(self, file_id):
        audio_file = self.get_file(file_id)
        if not audio_file:
            with self.current_audio_lock:
                self.current_audio = f"Unknown ID: {file_id}"
            return

        with self.current_audio_lock:
            self.current_audio = audio_file
            
        if hasattr(self, 'audio_thread') and self.audio_thread.is_alive():
            self.playback_event.set()
            self.audio_thread.join()
            
        self.playback_event.clear()
        self.audio_thread = th.Thread(target=self._play_audio, args=(audio_file,))
        self.audio_thread.start()

    def _play_audio(self, audio_file):
        try:
            pg.mixer.music.load(f"/media/pi/{audio_file}")
            pg.mixer.music.play()
            
            while pg.mixer.music.get_busy() and not self.playback_event.is_set():
                pg.time.Clock().tick(10)
                
        except Exception as e:
            print(f"An error occurred: {str(e)}")
        finally:
            with self.current_audio_lock:
                if self.current_audio == audio_file:
                    self.current_audio = None

    def stop(self):
        self.playback_event.set()
        pg.mixer.music.stop()
        with self.current_audio_lock:
            self.current_audio = None

    def get_file(self, file_id):
        record = self.session.query(RFIDAudio).filter_by(id=file_id).first()
        if record:
            return record.file
        else:
            return None
    
    def get_files_in_folder(self):
        folder_path = "/media/pi"
        return [file for file in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, file))]

    def add_file_to_db(self, file_id, file_name):
        record = self.session.query(RFIDAudio).filter_by(id=file_id).first()
        if record:
            record.file = file_name
        else:
            record = RFIDAudio(id=file_id, file=file_name)
            self.session.add(record)
        self.session.commit()

    def get_current_audio(self):
        with self.current_audio_lock:
            return self.current_audio

    def start_player(self):
        reader = SimpleMFRC522()
        current_id = 0
        none_counter = 0
        
        while True:
            if not self.reader_active:
                time.sleep(0.1)
                continue

            id, text = reader.read_no_block()
            if id is not None:
                if id != current_id:
                    current_id = id
                    self.play(str(id))
                    time.sleep(2)
            if id is None:
                none_counter += 1
            else:
                none_counter = 0
            
            if none_counter >= 2:
                self.stop()
                none_counter = 0
                current_id = 0
            
            time.sleep(0.1)

    def __del__(self):
        pg.mixer.quit()
        self.session.close() 

class OLEDMenu:
    def __init__(self):
        # Initialize OLED
        self.serial = i2c(port=1, address=0x3C)
        self.device = sh1106(self.serial)
        self.font = ImageFont.load_default()
        
        # Menu state
        self.menu_options = ["Currently Playing", "Add/Update Audio", "List Audios", "Exit"]
        self.menu_selection = 0
        self.yes_no_options = ["Yes", "No"]
        self.yes_no_selection = 0
        self.file_selection = 0
        self.option_confirmed = False
        
        # Button setup
        self.up = Button(24, bounce_time=0.05)
        self.down = Button(23, bounce_time=0.05)
        self.confirm = Button(22, bounce_time=0.05)
        
        # Button handlers
        self.up.when_pressed = self.on_up_pressed
        self.down.when_pressed = self.on_down_pressed
        self.confirm.when_pressed = self.on_confirm_pressed

    def display_menu(self):
        with canvas(self.device) as draw:
            draw.text((0, 0), "RFID Audio Player", font=self.font, fill="white")
            for i, option in enumerate(self.menu_options):
                y_pos = 16 + (i * 12)  # Start menu items below title
                prefix = ">" if i == self.menu_selection else " "
                draw.text((0, y_pos), f"{prefix} {option}", font=self.font, fill="white")

    def display_yes_no_menu(self):
        with canvas(self.device) as draw:
            draw.text((0, 0), "Overwrite?", font=self.font, fill="white")
            draw.text((0, 16), "Entry exists", font=self.font, fill="white")
            for i, option in enumerate(self.yes_no_options):
                y_pos = 32 + (i * 12)
                prefix = ">" if i == self.yes_no_selection else " "
                draw.text((0, y_pos), f"{prefix} {option}", font=self.font, fill="white")

    def display_file_menu(self, files):
        with canvas(self.device) as draw:
            draw.text((0, 0), "Select File:", font=self.font, fill="white")
            
            # Show 4 files at a time, with selection in the middle when possible
            visible_files = files[max(0, self.file_selection - 1):self.file_selection + 3]
            for i, file in enumerate(visible_files):
                y_pos = 16 + (i * 12)
                is_selected = (i == 1 if self.file_selection > 0 else i == 0)
                prefix = ">" if is_selected else " "
                # Truncate filename to fit screen
                truncated_file = file[:18] if len(file) > 18 else file
                draw.text((0, y_pos), f"{prefix} {truncated_file}", font=self.font, fill="white")

    def display_current_audio(self, current_audio):
        with canvas(self.device) as draw:
            draw.text((0, 0), "Now Playing:", font=self.font, fill="white")
            if current_audio:
                # Split long filenames across multiple lines
                if len(current_audio) > 18:
                    draw.text((0, 16), current_audio[:18], font=self.font, fill="white")
                    draw.text((0, 28), current_audio[18:36], font=self.font, fill="white")
                else:
                    draw.text((0, 16), current_audio, font=self.font, fill="white")
            else:
                draw.text((0, 16), "No audio playing", font=self.font, fill="white")
            draw.text((0, 48), "Press OK to return", font=self.font, fill="white")

    def display_message(self, message):
        with canvas(self.device) as draw:
            # Split message into multiple lines if needed
            words = message.split()
            lines = []
            current_line = []
            
            for word in words:
                if len(' '.join(current_line + [word])) <= 18:
                    current_line.append(word)
                else:
                    lines.append(' '.join(current_line))
                    current_line = [word]
            lines.append(' '.join(current_line))
            
            for i, line in enumerate(lines[:4]):  # Show up to 4 lines
                draw.text((0, i * 16), line, font=self.font, fill="white")

    def on_up_pressed(self):
        if self.current_menu == "main":
            self.menu_selection = (self.menu_selection - 1) % len(self.menu_options)
        elif self.current_menu == "yes_no":
            self.yes_no_selection = (self.yes_no_selection - 1) % len(self.yes_no_options)
        elif self.current_menu == "files":
            self.file_selection = (self.file_selection - 1) % len(self.file_options)
        self.update_display()

    def on_down_pressed(self):
        if self.current_menu == "main":
            self.menu_selection = (self.menu_selection + 1) % len(self.menu_options)
        elif self.current_menu == "yes_no":
            self.yes_no_selection = (self.yes_no_selection + 1) % len(self.yes_no_options)
        elif self.current_menu == "files":
            self.file_selection = (self.file_selection + 1) % len(self.file_options)
        self.update_display()

    def on_confirm_pressed(self):
        self.option_confirmed = True

    def update_display(self):
        if self.current_menu == "main":
            self.display_menu()
        elif self.current_menu == "yes_no":
            self.display_yes_no_menu()
        elif self.current_menu == "files":
            self.display_file_menu(self.file_options)

def main():
    audio = Audio()  # Your existing Audio class
    oled_menu = OLEDMenu()
    
    # Start the RFID reader thread
    player_thread = th.Thread(target=audio.start_player, daemon=True)
    player_thread.start()
    reader = SimpleMFRC522()

    while True:
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
                oled_menu.display_message("Hold RFID chip")
                id, text = reader.read()
                
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
                oled_menu.display_message(f"Added: {selected_file}")
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

        elif oled_menu.menu_selection == 3:  # Exit
            oled_menu.display_message("Goodbye!")
            time.sleep(1)
            break

if __name__ == "__main__":
    main()