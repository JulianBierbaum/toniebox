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
            print("Playing audio: " + self.file)

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

def main():
    audio = Audio()
    reader = SimpleMFRC522()
    current_id = None
    none_counter = 0

    while True:
        id, text = reader.read_no_block()

        if id is not None:
            if id != current_id:
                current_id = id
                print(f"RFID ID read: {id}")

                print("Options:")
                print("1. Play associated file")
                print("2. Add a new file to this ID")
                print("3. Skip")

                option = input("Select an option: ")

                if option == "1":
                    audio.play(str(id))

                elif option == "2":
                    print("Available files:")
                    files = audio.get_files_in_folder()
                    for i, file in enumerate(files):
                        print(f"{i + 1}. {file}")

                    file_choice = input("Select the file number to associate: ")
                    try:
                        file_choice = int(file_choice)
                        if 1 <= file_choice <= len(files):
                            audio.add_file_to_db(str(id), files[file_choice - 1])
                            print(f"File {files[file_choice - 1]} associated with ID {id}.")
                        else:
                            print("Invalid file choice.")
                    except ValueError:
                        print("Invalid input. Please enter a number.")

                elif option == "3":
                    print("Skipping...")

                else:
                    print("Invalid option.")

                time.sleep(2)  # Debounce

        if id is None:
            none_counter += 1
        else:
            none_counter = 0

        if none_counter >= 2:
            audio.stop()
            none_counter = 0
            current_id = None

        time.sleep(0.1)

if __name__ == "__main__":
    main()
