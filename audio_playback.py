import pygame as pg
import threading as th
from mfrc522 import SimpleMFRC522
from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import time
import os
from threading import Lock, Event

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
        return record.file if record else None

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

def menu(audio):
    while True:
        os.system('clear')
        print("=== RFID Audio Player Menu ===")
        print("1. View currently playing")
        print("2. Add new song")
        print("3. List songs in directory")
        print("3. Exit")
        choice = input("> ").strip()

        if choice == "1":
            current = audio.get_current_audio()
            print(f"\nCurrently Playing: {current}" if current else "\nNo song is playing.")
            input("\nPress Enter to return to the menu.")
        elif choice == "2":
            add_song_to_db(audio)
        elif choice == "3":
            print("Exiting...")
            break
        else:
            print("\nInvalid choice. Please try again.")
            input("\nPress Enter to return to the menu.")

def add_song_to_db(audio):
    session = audio.session
    try:
        rfid_id = input("Enter RFID ID (unique): ").strip()
        if not rfid_id:
            print("\nRFID ID cannot be empty.")
            input("\nPress Enter to return to the menu.")
            return
        
        existing = session.query(RFIDAudio).filter_by(id=rfid_id).first()
        if existing:
            print("\nRFID ID already exists in the database.")
            input("\nPress Enter to return to the menu.")
            return

        file_path = input("Enter audio file name (e.g., song.mp3): ").strip()
        if not file_path:
            print("\nAudio file name cannot be empty.")
            input("\nPress Enter to return to the menu.")
            return

        if not os.path.exists(f"/media/pi/{file_path}"):
            print("\nAudio file not found. Please ensure the file is in the correct directory.")
            input("\nPress Enter to return to the menu.")
            return

        new_record = RFIDAudio(id=rfid_id, file=file_path)
        session.add(new_record)
        session.commit()
        print("\nNew song added successfully!")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
    finally:
        input("\nPress Enter to return to the menu.")

def main():
    audio = Audio()
    player_thread = th.Thread(target=audio.start_player, daemon=True)
    player_thread.start()

    menu(audio)

if __name__ == "__main__":
    main()
