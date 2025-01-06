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
import select
import sys

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

up = Button(24, bounce_time=0.1)
down = Button(23, bounce_time=0.1)
confirm = Button(22, bounce_time=0.1)

menu_options = ["View currently playing", "Add or update audio", "List audios in directory", "Exit"]
current_selection = 0
menu_confirmed = False

# Global variables for overwrite confirmation
overwrite_options = ["Yes", "No"]
overwrite_selection = 0
overwrite_confirmed = False

# Global variables for selecting audio
audio_selection = 0
audio_confirmed = False

audio = Audio()
files = audio.get_files_in_folder()

def on_up_pressed():
    global current_selection
    current_selection = (current_selection - 1) % len(menu_options)
    display_menu()

def on_down_pressed():
    global current_selection
    current_selection = (current_selection + 1) % len(menu_options)
    display_menu()

def on_confirm_pressed():
    global menu_confirmed
    menu_confirmed = True

def on_up_pressed_overwrite():
    global overwrite_selection
    overwrite_selection = (overwrite_selection - 1) % len(overwrite_options)
    display_overwrite_menu()

def on_down_pressed_overwrite():
    global overwrite_selection
    overwrite_selection = (overwrite_selection + 1) % len(overwrite_options)
    display_overwrite_menu()

def on_confirm_pressed_overwrite():
    global overwrite_confirmed
    overwrite_confirmed = True

def on_up_pressed_audio():
    global audio_selection
    audio_selection = (audio_selection - 1) % len(files)
    display_audio_menu(files)

def on_down_pressed_audio():
    global audio_selection
    audio_selection = (audio_selection + 1) % len(files)
    display_audio_menu(files)

def on_confirm_pressed_audio():
    global audio_confirmed
    audio_confirmed = True

up.when_pressed = on_up_pressed
down.when_pressed = on_down_pressed
confirm.when_pressed = on_confirm_pressed

# Assign the buttons to overwrite and audio selection
up.when_pressed = on_up_pressed_overwrite
down.when_pressed = on_down_pressed_overwrite
confirm.when_pressed = on_confirm_pressed_overwrite

up.when_pressed = on_up_pressed_audio
down.when_pressed = on_down_pressed_audio
confirm.when_pressed = on_confirm_pressed_audio

def display_menu():
    os.system('clear')
    print("=== RFID Audio Player Menu ===")
    for i, option in enumerate(menu_options):
        if i == current_selection:
            print(f"> {option} <")
        else:
            print(f"  {option}")

def display_overwrite_menu():
    os.system('clear')
    print("=== Overwrite Confirmation ===")
    for i, option in enumerate(overwrite_options):
        if i == overwrite_selection:
            print(f"> {option} <")
        else:
            print(f"  {option}")

def display_audio_menu(files):
    os.system('clear')
    print("\n=== Available Audios ===")
    for i, file in enumerate(files):
        if i == audio_selection:
            print(f"> {file} <")
        else:
            print(f"  {file}")

def main():
    global menu_confirmed, overwrite_confirmed, audio_confirmed
    player_thread = th.Thread(target=audio.start_player, daemon=True)
    player_thread.start()
    reader = SimpleMFRC522()

    while True:
        display_menu()
        menu_confirmed = False

        while not menu_confirmed:
            time.sleep(0.1)

        if current_selection == 0:
            print("\n=== Currently Playing ===")
            try:
                while True:
                    current = audio.get_current_audio()
                    os.system('clear')
                    print("\n=== Currently Playing ===")
                    print(f"audio: {current}" if current else "No audio is playing.")
                    print("\n(Press Enter to return to the menu.)")
                    time.sleep(0.5)

                    if select.select([sys.stdin], [], [], 0.0)[0]:
                        break
            except KeyboardInterrupt:
                pass

        elif current_selection == 1:
            print("\n=== Current Database Entries ===")
            entries = audio.session.query(RFIDAudio).all()
            if entries:
                for entry in entries:
                    print(f"ID: {entry.id}, File: {entry.file}")
            print("\n")

            try:
                print("Hold RFID chip to reader.")
                id, text = reader.read()
                print(f"RFID ID: {id}")

                existing = audio.session.query(RFIDAudio).filter_by(id=id).first()
                if existing:
                    print(f"\nRFID ID {id} already exists with file: {existing.file}.")
                    print("Navigate using buttons and confirm overwrite.")
                    overwrite_confirmed = False
                    while not overwrite_confirmed:
                        time.sleep(0.1)
                    
                    if overwrite_selection == 0:  # Yes
                        print(f"\nOverwriting with new file for ID {id}.")
                    else:  # No
                        print("\nEntry not updated.")
                        menu_confirmed = False
                        continue

                files = audio.get_files_in_folder()
                if not files:
                    print("\nNo audio files found in the directory.")
                    menu_confirmed = False
                    while not menu_confirmed:
                        time.sleep(0.1)
                    continue

                print("\nAvailable audios:")
                for i, file in enumerate(files, 1):
                    print(f"{i}. {file}")

                # Wait for button confirmation to select the audio
                audio_confirmed = False
                while not audio_confirmed:
                    time.sleep(0.1)

                selected_audio = files[audio_selection]
                audio.add_file_to_db(str(id), selected_audio)
                print(f"\nSuccessfully associated '{selected_audio}' with RFID ID {id}.")

            except Exception as e:
                print(f"\nAn error occurred: {str(e)}")
            finally:
                menu_confirmed = False
                while not menu_confirmed:
                    time.sleep(0.1)

        elif current_selection == 2:
            files = audio.get_files_in_folder()
            os.system('clear')
            print("\n=== Audios in Directory ===")
            if files:
                for i, file in enumerate(files, 1):
                    record = audio.session.query(RFIDAudio).filter_by(file=file).first()
                    if record:
                        print(f"{i}. {file} -> {record.id}")
                    else:
                        print(f"{i}. {file}")
            else:
                print("No audios found in the directory.")

            menu_confirmed = False
            while not menu_confirmed:
                time.sleep(0.1)
            continue

        elif current_selection == 3:
            print("Exiting...")
            break

if __name__ == "__main__":
    main()
