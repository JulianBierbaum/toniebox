import pygame as pg
import threading as th
from mfrc522 import SimpleMFRC522
from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import time
import os
import queue

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

def ui_thread(queue):
    while True:
        if queue.empty():
            print("Options:")
            print("1. View available files")
            print("2. Add file to database")
            print("3. Exit")

            option = input("Select an option: ")

            if option == "1":
                audio = Audio()
                print("Available files:")
                files = audio.get_files_in_folder()
                for i, file in enumerate(files):
                    print(f"{i + 1}. {file}")

            elif option == "2":
                audio = Audio()
                rfid_id = input("Enter RFID ID to associate with a file: ")
                print("Available files:")
                files = audio.get_files_in_folder()
                for i, file in enumerate(files):
                    print(f"{i + 1}. {file}")

                file_choice = input("Select the file number to associate: ")
                try:
                    file_choice = int(file_choice)
                    if 1 <= file_choice <= len(files):
                        audio.add_file_to_db(rfid_id, files[file_choice - 1])
                        print(f"File {files[file_choice - 1]} associated with ID {rfid_id}.")
                    else:
                        print("Invalid file choice.")
                except ValueError:
                    print("Invalid input. Please enter a number.")

            elif option == "3":
                print("Exiting UI thread...")
                break

            else:
                print("Invalid option.")

        time.sleep(1)

def main():
    audio = Audio()
    reader = SimpleMFRC522()
    current_id = None
    none_counter = 0
    ui_queue = queue.Queue()

    ui = th.Thread(target=ui_thread, args=(ui_queue,), daemon=True)
    ui.start()

    while True:
        id, text = reader.read_no_block()

        if id is not None:
            if id != current_id:
                current_id = id
                ui_queue.put("ID_DETECTED")
                print(f"RFID ID read: {id}")

                file = audio.get_file(str(id))
                if file:
                    audio.play(str(id))
                else:
                    print("No file associated with this ID.")

                time.sleep(2)  # Debounce

        if id is None:
            none_counter += 1
            if none_counter >= 2:
                audio.stop()
                none_counter = 0
                current_id = None
                while not ui_queue.empty():
                    ui_queue.get()  # Clear queue

        time.sleep(0.1)

if __name__ == "__main__":
    main()
