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
            print(f"No audio file mapped for id: {file_id}")
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
            print(f"Playing audio: {audio_file}")
            
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
        current_id = None
        
        while True:
            id, text = reader.read_no_block()
            if id and id != current_id:
                current_id = id
                self.play(str(id))
            elif not id:
                self.stop()
                current_id = None
            time.sleep(0.5)

    def __del__(self):
        pg.mixer.quit()
        self.session.close()

def display_current_audio(audio):
    while True:
        os.system('clear')
        current = audio.get_current_audio()
        print("=== RFID Audio Player ===")
        print(f"Currently Playing: {current}" if current else "No song is playing.")
        time.sleep(0.1)

def main():
    audio = Audio()
    player_thread = th.Thread(target=audio.start_player, daemon=True)
    player_thread.start()
    display_current_audio(audio)

if __name__ == "__main__":
    main()
