"""
OLED display and menu system for the RFID Audio Player with KY-040 encoder.

This module provides a UI for the RFID Audio Player using an OLED display
and a rotary encoder for navigation with performance optimizations.
"""

import queue
import threading
import time

from gpiozero import Button, RotaryEncoder
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from PIL import Image, ImageDraw, ImageFont

from logger import get_logger

logger = get_logger(__name__)


class OLEDMenu:
    """
    A class to handle the OLED display and menu system with rotary encoder.

    This class provides methods to display and navigate menus on the OLED
    screen using a KY-040 rotary encoder for navigation and its switch
    for confirmation. Uses a dedicated display thread for better performance.
    """

    def __init__(self, encoder_clk=17, encoder_dt=20, confirm_pin=16):
        """
        Initialize the OLED display and input controls.

        Args:
            encoder_clk (int): GPIO pin for encoder CLK (rotary pin A)
            encoder_dt (int): GPIO pin for encoder DT (rotary pin B)
            confirm_pin (int): GPIO pin for encoder switch (confirm button)
        """
        logger.info("Initializing OLED menu system")
        # Initialize OLED
        try:
            self.serial = i2c(port=1, address=0x3C)
            self.device = sh1106(self.serial)
            self.font = ImageFont.load_default()
            logger.info("OLED display initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OLED display: {e}")
            raise

        # Menu state
        self.menu_options = ["Currently Playing", "Add/Update Audio", "List Audios"]
        self.menu_selection = 0
        self.yes_no_options = ["Yes", "No"]
        self.yes_no_selection = 0
        self.file_selection = 0
        self.file_options = []
        self.option_confirmed = False
        self.current_menu = "main"

        self.width = 128
        self.height = 64
        self.image = Image.new("1", (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)

        # Thread safety
        self.display_lock = threading.Lock()
        self.menu_lock = threading.Lock()
        self.update_queue = queue.Queue()
        self.running = True

        # Input controls setup
        try:
            self.encoder = RotaryEncoder(encoder_clk, encoder_dt, bounce_time=0.01)
            self.confirm = Button(confirm_pin, bounce_time=0.01)

            # Event handlers
            self.encoder.when_rotated = self.handle_rotation
            self.confirm.when_pressed = self.on_confirm_pressed
            logger.info("Input controls initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize input controls: {e}")
            raise

        # Start display thread
        self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self.display_thread.start()
        logger.info("Display thread started")

    def _display_loop(self):
        """Background thread for handling display updates"""
        logger.info("Display loop started")
        last_update = 0
        min_update_interval = 0.03  # ~30fps cap to prevent screen tearing

        while self.running:
            try:
                # Process display update requests
                try:
                    # Non-blocking queue check
                    update_type = self.update_queue.get_nowait()
                    current_time = time.time()

                    # Enforce minimum update interval
                    if current_time - last_update >= min_update_interval:
                        with self.menu_lock:
                            self._update_display_internal(update_type)
                        last_update = current_time

                    self.update_queue.task_done()
                except queue.Empty:
                    # No updates in queue, sleep briefly
                    time.sleep(0.01)
            except Exception as e:
                logger.error(f"Error in display thread: {e}")
                time.sleep(0.1)  # Prevent tight error loop

    def _update_display_internal(self, update_type):
        """Internal method to update the display based on menu state"""
        # Clear the image buffer
        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)

        if update_type == "main":
            self._draw_main_menu()
        elif update_type == "yes_no":
            self._draw_yes_no_menu()
        elif update_type == "files":
            self._draw_file_menu()
        elif update_type == "current":
            current = (
                self.get_current_audio() if hasattr(self, "get_current_audio") else None
            )
            self._draw_current_audio(current)
        elif update_type.startswith("message:"):
            message = update_type[8:]  # Extract message from update_type
            self._draw_message(message)

        # Push buffer to display
        self.device.display(self.image)

    def handle_rotation(self):
        """
        Handle rotary encoder rotation events.
        Only process rotation in menus where it makes sense.
        """
        if (
            self.current_menu == "currently_playing"
            or self.current_menu == "add_update"
        ):
            self.encoder.steps = 0
            return

        # Get the current state of the encoder
        steps = self.encoder.steps
        if steps != 0:
            with self.menu_lock:
                if steps > 0:
                    for _ in range(min(steps, 3)):
                        self._change_selection(1)  # Down
                else:
                    for _ in range(min(abs(steps), 3)):
                        self._change_selection(-1)  # Up

            # Reset the encoder steps after processing
            self.encoder.steps = 0
            self.update_display()

    def _change_selection(self, direction):
        """
        Change selection based on direction.

        Args:
            direction (int): 1 for increment, -1 for decrement
        """
        if self.current_menu == "main":
            self.menu_selection = (self.menu_selection + direction) % len(
                self.menu_options
            )
            logger.debug(
                f"Main menu selection changed to: {self.menu_options[self.menu_selection]}"
            )
        elif self.current_menu == "yes_no":
            self.yes_no_selection = (self.yes_no_selection + direction) % len(
                self.yes_no_options
            )
            logger.debug(
                f"Yes/No selection changed to: {self.yes_no_options[self.yes_no_selection]}"
            )
        elif self.current_menu == "files" and self.file_options:
            self.file_selection = (self.file_selection + direction) % len(
                self.file_options
            )
            logger.debug(
                f"File selection changed to: {self.file_options[self.file_selection]}"
            )

    def on_confirm_pressed(self):
        """Handle confirmation"""
        self.option_confirmed = True
        logger.debug(f"Selection confirmed in menu: {self.current_menu}")

    def _draw_menu_items(
        self, items, selection, start_y=16, prefix_selected=">", prefix_normal=" "
    ):
        """
        Draw a list of menu items with selection indicator.

        Args:
            items: List of items to display
            selection: Index of selected item
            start_y: Starting Y position for first item
            prefix_selected: Prefix for selected item
            prefix_normal: Prefix for non-selected items
        """
        # For file menu with many items, show a sliding window around the selection
        if len(items) > 3 and self.current_menu == "files":
            start_idx = max(0, min(selection, len(items) - 3))
            visible_items = items[start_idx : start_idx + 3]
            selection_offset = selection - start_idx

            for i, item in enumerate(visible_items):
                y_pos = start_y + (i * 12)
                prefix = prefix_selected if i == selection_offset else prefix_normal
                # Truncate long filenames
                if len(item) > 18:
                    item = item[:18]
                self.draw.text((0, y_pos), f"{prefix} {item}", font=self.font, fill=255)
        else:
            # Standard menu display (all items visible)
            for i, item in enumerate(items):
                y_pos = start_y + (i * 12)
                prefix = prefix_selected if i == selection else prefix_normal
                self.draw.text((0, y_pos), f"{prefix} {item}", font=self.font, fill=255)

    def _draw_main_menu(self):
        """Draw the main menu to the image buffer"""
        self.draw.text((0, 0), "RFID Audio Player", font=self.font, fill=255)
        self._draw_menu_items(self.menu_options, self.menu_selection)

    def _draw_yes_no_menu(self):
        """Draw the yes/no menu to the image buffer"""
        self.draw.text((0, 0), "Overwrite?", font=self.font, fill=255)
        self.draw.text((0, 16), "Entry exists", font=self.font, fill=255)
        self._draw_menu_items(self.yes_no_options, self.yes_no_selection, start_y=32)

    def _draw_file_menu(self):
        """Draw the file selection menu to the image buffer"""
        self.draw.text((0, 0), "Files:", font=self.font, fill=255)
        self._draw_menu_items(self.file_options, self.file_selection)

    def _draw_current_audio(self, current_audio):
        """Draw the currently playing screen to the image buffer"""
        self.draw.text((0, 0), "Now Playing:", font=self.font, fill=255)
        if current_audio:
            if len(current_audio) > 18:
                self.draw.text((0, 16), current_audio[:18], font=self.font, fill=255)
                self.draw.text((0, 28), current_audio[18:36], font=self.font, fill=255)
            else:
                self.draw.text((0, 16), current_audio, font=self.font, fill=255)
        else:
            self.draw.text((0, 16), "No audio playing", font=self.font, fill=255)
        self.draw.text((0, 48), "Press OK to return", font=self.font, fill=255)

    def _draw_message(self, message):
        """Draw a message to the image buffer"""
        # Split the message into lines that fit the display
        lines = self._wrap_text_to_lines(message, max_chars=18)
        for i, line in enumerate(lines[:4]):  # Display up to 4 lines
            self.draw.text((0, i * 16), line, font=self.font, fill=255)

    def display_menu(self):
        """Queue a main menu display update."""
        logger.debug("Displaying main menu")
        self.update_queue.put("main")

    def display_yes_no_menu(self):
        """Queue a yes/no menu display update."""
        logger.debug("Displaying yes/no menu")
        self.update_queue.put("yes_no")

    def display_file_menu(self, files):
        """
        Queue a file menu display update.

        Args:
            files (list): List of filenames to display
        """
        logger.debug(f"Displaying file menu with {len(files)} files")
        with self.menu_lock:
            self.file_options = files
        self.update_queue.put("files")

    def display_current_audio(self, current_audio):
        """
        Queue a currently playing display update.

        Args:
            current_audio (str or None): Currently playing audio filename or None
        """
        logger.debug(f"Displaying current audio: {current_audio}")
        self.update_queue.put("current")

    def display_message(self, message):
        """
        Queue a message display update.

        Args:
            message (str): Message to display
        """
        logger.debug(f"Displaying message: {message[:20]}...")
        self.update_queue.put(f"message:{message}")

    def _wrap_text_to_lines(self, text, max_chars=18):
        """
        Split text into lines with word wrapping.

        Args:
            text (str): Text to wrap
            max_chars (int): Maximum characters per line

        Returns:
            list: List of wrapped text lines
        """
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            # If adding this word exceeds max length
            if len(" ".join(current_line + [word])) <= max_chars:
                current_line.append(word)
            else:
                # Add the current line and start a new one
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        # Add the last line if not empty
        if current_line:
            lines.append(" ".join(current_line))

        return lines

    def update_display(self):
        """Queue a display update based on current menu state."""
        if self.current_menu == "main":
            self.update_queue.put("main")
        elif self.current_menu == "yes_no":
            self.update_queue.put("yes_no")
        elif self.current_menu == "files" and self.file_options:
            self.update_queue.put("files")
        elif self.current_menu == "currently_playing":
            self.update_queue.put("current")

    def wait_for_confirmation(self, timeout=None):
        """
        Wait for confirmation with optional timeout.

        Args:
            timeout (float, optional): Maximum time to wait in seconds

        Returns:
            bool: True if confirmed, False if timed out
        """
        logger.debug(f"Waiting for confirmation with timeout: {timeout}s")
        self.option_confirmed = False
        start_time = time.time()
        while not self.option_confirmed:
            if timeout and (time.time() - start_time > timeout):
                logger.debug("Confirmation wait timed out")
                return False
            time.sleep(0.1)
        logger.debug("Received confirmation")
        return True

    def shutdown(self):
        """Clean up resources and stop the display thread"""
        logger.info("Shutting down OLED menu system")
        self.running = False
        if self.display_thread.is_alive():
            self.display_thread.join(timeout=1.0)

    def __del__(self):
        """Destructor to clean up resources"""
        self.shutdown()
