import pygame as pg
import threading as th
from mfrc522 import SimpleMFRC522
from sqlalchemy import create_engine, Column, String, orm
from sqlalchemy.orm import sessionmaker
import time
import os
from threading import Lock, Event
from gpiozero import Button

Base = orm.declarative_base()
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

def on_up_pressed():
    global current_selection
    current_selection = (current_selection - 1) % len(menu_options)
    display_menu()

def on_down_pressed():
    global current_selection
    current_selection = (current_selection + 1) % len(menu_options)
    display_menu()

def on_confirm_pressed():
    global current_selection
    if current_selection == 0:  # View currently playing
        display_current_audio()
    elif current_selection == 1:  # Add or update audio
        add_update_audio()
    elif current_selection == 2:  # List audios in directory
        list_audios()
    elif current_selection == 3:  # Exit
        print("Exiting...")
        exit()

up.when_pressed = on_up_pressed
down.when_pressed = on_down_pressed
confirm.when_pressed = on_confirm_pressed

def display_current_audio():
    os.system('clear')
    print("\n=== Currently Playing ===")
    current = audio.get_current_audio()
    print(f"Audio: {current if current else 'No audio is playing.'}")
    print("\nPress the Confirm button to return to the menu.")
    while True:
        if confirm.is_pressed:
            break
        time.sleep(0.1)

def display_menu():
    os.system('clear')
    print("=== RFID Audio Player Menu ===")
    for i, option in enumerate(menu_options):
        if i == current_selection:
            print(f"> {option} <")
        else:
            print(f"  {option}")

def add_update_audio():
    reader = SimpleMFRC522()

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
            overwrite = input("Do you want to overwrite this entry? (yes/no): ").strip().lower()
            if overwrite != "yes":
                print("\nEntry not updated.")
                return

        files = audio.get_files_in_folder()
        if not files:
            print("\nNo audio files found in the directory.")
            return

        print("\nAvailable audios:")
        for i, file in enumerate(files, 1):
            print(f"{i}. {file}")

        try:
            choice = int(input("\nEnter the number of the audio to associate with the RFID: ").strip())
            if 1 <= choice <= len(files):
                file_path = files[choice - 1]
                audio.add_file_to_db(str(id), file_path)
                print(f"\nSuccessfully associated '{file_path}' with RFID ID {id}.")
            else:
                print("\nInvalid choice. Please select a valid number.")
        except ValueError:
            print("\nInvalid input. Please enter a number.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")

def list_audios():
    files = audio.get_files_in_folder()
    os.system('clear')
    if files:
        print("Audios in Directory:")
        for i, file in enumerate(files, 1):
            print(f"{i}. {file}")
    else:
        print("No audios found in the directory.")
    while not confirm.is_pressed:
        time.sleep(0.1)

def main():
    global audio
    audio = Audio()
    player_thread = th.Thread(target=audio.start_player, daemon=True)
    player_thread.start()

    while True:
        display_menu()
        time.sleep(0.1)

if __name__ == "__main__":
    main()
