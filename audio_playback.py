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

up = Button(24, bounce_time=0.05)
down = Button(23, bounce_time=0.05)
confirm = Button(22, bounce_time=0.05)

menu_options = ["View currently playing", "Add or update audio", "List audios in directory", "Exit"]
menu_selection = 0

yes_no_options = ["Yes", "No"]
yes_no_selection = 0

option_confirmed = False

def on_up_pressed():
    global menu_selection
    menu_selection = (menu_selection - 1) % len(menu_options)
    display_menu()

def on_down_pressed():
    global menu_selection
    menu_selection = (menu_selection + 1) % len(menu_options)
    display_menu()

def on_yes_no_up_pressed():
    global yes_no_selection
    yes_no_selection = (yes_no_selection - 1) % len(yes_no_options)
    display_yes_no_menu()

def on_yes_no_down_pressed():
    global yes_no_selection
    yes_no_selection = (yes_no_selection + 1) % len(yes_no_options)
    display_yes_no_menu()

def on_confirm_pressed():
    global option_confirmed
    option_confirmed = True

up.when_pressed = on_up_pressed
down.when_pressed = on_down_pressed
confirm.when_pressed = on_confirm_pressed

def display_menu():
    os.system('clear')
    print("=== RFID Audio Player Menu ===")
    for i, option in enumerate(menu_options):
        if i == menu_selection:
            print(f"> {option}")
        else:
            print(f"  {option}")

def display_yes_no_menu():
    os.system('clear')
    print("=== Overwrite Confirmation ===")
    print("\nAn entry with this id is already in the database")
    print("Do you want to overwrite this entry?")
    for i, option in enumerate(yes_no_options):
        if i == yes_no_selection:
            print(f"> {option}")
        else:
            print(f"  {option}")

def main():
    global option_confirmed
    audio = Audio()
    player_thread = th.Thread(target=audio.start_player, daemon=True)
    player_thread.start()
    reader = SimpleMFRC522()

    while True:
        display_menu()
        option_confirmed = False

        while not option_confirmed:
            time.sleep(0.1)

        if menu_selection == 0:
            option_confirmed = False

            print("\n=== Currently Playing ===")
            try:
                while True:
                    current = audio.get_current_audio()
                    os.system('clear')
                    print("\n=== Currently Playing ===")
                    print(f"audio: {current}" if current else "No audio is playing.")
                    print("\n(Press Confirm button to return to the menu.)")
                    time.sleep(0.5)

                    if option_confirmed:
                        break
            except option_confirmed:
                pass

        elif menu_selection == 1:
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
                    up.when_pressed = on_yes_no_up_pressed
                    down.when_pressed = on_yes_no_down_pressed

                    display_yes_no_menu()
                    option_confirmed = False

                    while not option_confirmed:
                        time.sleep(0.1)
                    
                    up.when_pressed = on_up_pressed
                    down.when_pressed = on_down_pressed
                    confirm.when_pressed = on_confirm_pressed

                    if yes_no_selection == 1:
                        print("\nEntry not updated.")
                        option_confirmed = False
                        time.sleep(0.1)
                        continue


                files = audio.get_files_in_folder()
                if not files:
                    print("\nNo audio files found in the directory.")
                    option_confirmed = False
                    while not option_confirmed:
                        time.sleep(0.1)
                    continue

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
            finally:
                option_confirmed = False
                time.sleep(0.1)
                continue

        elif menu_selection == 2:
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

            option_confirmed = False
            while not option_confirmed:
                time.sleep(0.1)
            continue

        elif menu_selection == 3:
            print("Exiting...")
            break

if __name__ == "__main__":
    main()

