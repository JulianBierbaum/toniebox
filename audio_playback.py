import pygame as pg
import threading as th
from mfrc522 import SimpleMFRC522
from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import time
import os

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

    def play(self, file_id):
        file = self.get_file(file_id)
        if not file:
            print(f"No audio file mapped for id: {file_id}")
            return

        self.file = f"/media/pi/INTENSO/{file}"
        self.audio_thread = th.Thread(target=self._play_audio).start()

    def _play_audio(self):
        try:
            pg.mixer.music.load(self.file)
            pg.mixer.music.play()
            print("playing audio: " + self.file)

            while pg.mixer.music.get_busy():
                pg.time.Clock().tick(10)
        except Exception as e:
            print(f"An error occurred: {str(e)}")

    def stop(self):
        pg.mixer.music.stop()

    def get_file(self, file_id):
        record = self.session.query(RFIDAudio).filter_by(id=file_id).first()
        return record.file if record else None

    def get_files_in_folder(self):
        folder_path = "/media/pi/INTENSO"
        return [file for file in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, file))]

    def add_file_to_db(self, file_id, file_name):
        record = self.session.query(RFIDAudio).filter_by(id=file_id).first()
        if record:
            record.file = file_name
        else:
            record = RFIDAudio(id=file_id, file=file_name)
            self.session.add(record)
        self.session.commit()

    def __del__(self):
        pg.mixer.quit()
        self.session.close()

audio = Audio()
reader = SimpleMFRC522()
current_id = 0
none_counter = 0

print(audio.get_files_in_folder())

while True:
    id, text = reader.read_no_block()
    print(id)

    if id is not None:
        if id != current_id:
            current_id = id
            audio.play(str(id))
        time.sleep(2)

    if id is None:
        none_counter += 1
    else:
        none_counter = 0

    if none_counter >= 2:
        audio.stop()
        none_counter = 0
        current_id = 0

    time.sleep(0.1)
