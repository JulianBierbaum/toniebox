"""
OLED display and menu system for the RFID Audio Player with KY-040 encoder.

This module provides a UI for the RFID Audio Player using an OLED display
and a rotary encoder for navigation.
"""

import time
import os

from gpiozero import Button, RotaryEncoder
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106
from luma.core.error import DeviceNotFoundError
from PIL import ImageFont
import threading

from .logger import get_logger
from dotenv import load_dotenv

load_dotenv()

logger = get_logger(__name__)


class OLEDMenu:
    def __init__(
        self,
        encoder_clk=os.getenv("ENCODER_CLK"),
        encoder_dt=os.getenv("ENCODER_DT"),
        confirm_pin=os.getenv("ENCODER_CONFIRM"),
    ):
        logger.info("Initializing OLED menu system")
        self.display_available = self._initialize_display()
        
        # Threading synchronization
        self.lock = threading.Lock()
        self.shutdown_event = threading.Event()
        self.needs_redraw = True
        
        # Menu states

        # Menu states
        self.menu_options = [
            "Currently Playing",
            "Add/Update Audio",
            "List Audios",
            "Audio Settings",
        ]
        self.menu_selection = 0
        self.yes_no_options = ["Yes", "No"]
        self.yes_no_selection = 0
        self.file_selection = 0
        self.file_options = []
        self.option_confirmed = False
        self.current_menu = "main"

        self.audio_output_options = ["Speaker", "AUX"]
        self.audio_output_selection = 0

        self.audio_menu_options = ["Back", "Volume", "Output Device"]
        self.audio_menu_selection = 1
        self.adjusting_volume = False

        self.volume_value = int(os.getenv("DEFAULT_VOLUME", 50))
        logger.info(f"Loaded DEFAULT_VOLUME: {self.volume_value}")

        try:
            self.encoder_bounce_time = os.getenv("ENCODER_BOUNCE_TIME", 0.02)
            self.encoder = RotaryEncoder(
                encoder_clk, encoder_dt, bounce_time=float(self.encoder_bounce_time)
            )
            self.confirm = Button(
                confirm_pin, bounce_time=float(self.encoder_bounce_time)
            )

            self.confirm.when_pressed = self.on_confirm_pressed
            logger.info("Input controls initialized successfully")
            
            # Start render thread
            self.render_thread = threading.Thread(target=self._render_loop, daemon=True)
            self.render_thread.start()
            logger.info("Render thread started")
        except Exception as e:
            logger.error(f"Failed to initialize input controls: {e}")
            raise

    def _render_loop(self):
        """Background thread for rendering the display."""
        while not self.shutdown_event.is_set():
            if self.display_available and self.needs_redraw:
                with self.lock:
                    self.update_display()
                self.needs_redraw = False
            time.sleep(0.033)  # Cap at ~30 FPS

    def stop(self):
        """Stop the render thread."""
        self.shutdown_event.set()
        if hasattr(self, 'render_thread'):
            self.render_thread.join(timeout=1.0)

    def _initialize_display(self):
        try:
            i2c_address = int(os.getenv("I2C_ADDRESS", "0x3C"), 16)
            self.serial = i2c(port=1, address=i2c_address)
            self.device = sh1106(self.serial)
            self.font = ImageFont.load_default()
            logger.info("OLED display initialized successfully")
            return True
        except DeviceNotFoundError:
            logger.error("OLED display not found on I2C address 0x3C.")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error initializing OLED display: {e}")
            return False

    def _safe_draw(self, draw_function):
        if not self.display_available:
            logger.warning("Attempted to draw while display is unavailable.")
            return
        try:
            with canvas(self.device) as draw:
                draw_function(draw)
        except Exception as e:
            logger.error(f"Error during OLED drawing: {e}")

    def handle_rotation(self):
        """
        Handle rotary encoder rotation events.
        Now includes volume adjustment mode.
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
            if (
                self.current_menu == "audio_menu"
                and self.audio_menu_selection == 1
                and self.adjusting_volume
            ):
                # Adjust volume
                self.volume_value = max(0, min(100, self.volume_value + steps * 5))
                logger.debug(f"Volume adjusted to: {self.volume_value}%")
            else:
                # Regular menu navigation
                if steps > 0:
                    for _ in range(steps):
                        self._change_selection(1)  # Down
                else:
                    for _ in range(abs(steps)):
                        self._change_selection(-1)  # Up

            self.encoder.steps = 0
            self.needs_redraw = True

    def _change_selection(self, direction):
        """
        Change selection based on direction.
        Now includes audio menu selections.
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
        elif self.current_menu == "audio_output":
            self.audio_output_selection = (
                self.audio_output_selection + direction
            ) % len(self.audio_output_options)
            logger.debug(
                f"Audio output selection changed to: {self.audio_output_options[self.audio_output_selection]}"
            )
        elif self.current_menu == "audio_menu":
            if not self.adjusting_volume or self.audio_menu_selection != 1:
                self.audio_menu_selection = (
                    self.audio_menu_selection + direction
                ) % len(self.audio_menu_options)
                logger.debug(
                    f"Audio menu selection changed to: {self.audio_menu_options[self.audio_menu_selection]}"
                )

    def on_confirm_pressed(self):
        """Handle confirmation"""
        with self.lock:
            self.option_confirmed = True
        logger.debug(f"Selection confirmed in menu: {self.current_menu}")

    def _draw_menu_items(
        self, draw, items, selection, start_y=16, prefix_selected=">", prefix_normal=" "
    ):
        """
        Draw a list of menu items with selection indicator.

        Args:
            draw: PIL drawing context
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
                draw.text((0, y_pos), f"{prefix} {item}", font=self.font, fill="white")
        else:
            # Standard menu display (all items visible)
            for i, item in enumerate(items):
                y_pos = start_y + (i * 12)
                prefix = prefix_selected if i == selection else prefix_normal
                draw.text((0, y_pos), f"{prefix} {item}", font=self.font, fill="white")

    def display_menu(self):
        logger.debug("Displaying main menu")
        self._safe_draw(
            lambda draw: (
                draw.text((0, 0), "RFID Audio Player", font=self.font, fill="white"),
                self._draw_menu_items(draw, self.menu_options, self.menu_selection),
            )
        )

    def display_yes_no_menu(self):
        logger.debug("Displaying yes/no menu")
        self._safe_draw(
            lambda draw: (
                draw.text((0, 0), "Overwrite?", font=self.font, fill="white"),
                draw.text((0, 16), "Entry exists", font=self.font, fill="white"),
                self._draw_menu_items(
                    draw, self.yes_no_options, self.yes_no_selection, start_y=32
                ),
            )
        )

    def display_file_menu(self, files):
        logger.debug(f"Displaying file menu with {len(files)} files")
        self._safe_draw(
            lambda draw: (
                draw.text((0, 0), "Files:", font=self.font, fill="white"),
                self._draw_menu_items(draw, files, self.file_selection),
            )
        )

    def display_current_audio(self, current_audio):
        logger.debug(f"Displaying current audio: {current_audio}")

        def draw_callback(draw):
            draw.text((0, 0), "Now Playing:", font=self.font, fill="white")
            if current_audio:
                if len(current_audio) > 18:
                    draw.text((0, 16), current_audio[:18], font=self.font, fill="white")
                    draw.text(
                        (0, 28), current_audio[18:36], font=self.font, fill="white"
                    )
                else:
                    draw.text((0, 16), current_audio, font=self.font, fill="white")
            else:
                draw.text((0, 16), "No audio playing", font=self.font, fill="white")
            draw.text((0, 48), "Press OK to return", font=self.font, fill="white")

        self._safe_draw(draw_callback)

    def display_audio_output_menu(self):
        logger.debug("Displaying audio output menu")
        self._safe_draw(
            lambda draw: (
                draw.text((0, 0), "Audio Output:", font=self.font, fill="white"),
                self._draw_menu_items(
                    draw, self.audio_output_options, self.audio_output_selection
                ),
            )
        )

    def display_message(self, message):
        logger.debug(f"Displaying message: {message[:20]}...")

        def draw_callback(draw):
            lines = self._wrap_text_to_lines(message, max_chars=18)
            for i, line in enumerate(lines[:4]):
                draw.text((0, i * 16), line, font=self.font, fill="white")

        self._safe_draw(draw_callback)

    def display_audio_menu(self):
        logger.debug("Displaying audio settings menu")

        def draw_callback(draw):
            draw.text((0, 0), "Audio Settings:", font=self.font, fill="white")
            for i, item in enumerate(self.audio_menu_options):
                y_pos = 16 + (i * 12)
                prefix = ">" if i == self.audio_menu_selection else " "
                draw.text((0, y_pos), f"{prefix} {item}", font=self.font, fill="white")

            if self.audio_menu_selection == 1:
                slider_y = 16 + 12 + 4
                slider_width = 48
                filled_width = int((self.volume_value / 100) * slider_width)

                draw.rectangle(
                    (50, slider_y, 50 + slider_width, slider_y + 6), outline="white"
                )

                if filled_width > 0:
                    draw.rectangle(
                        (50, slider_y, 50 + filled_width, slider_y + 6),
                        fill="white" if self.adjusting_volume else "white",
                        outline="white",
                    )
                draw.text(
                    (105, slider_y),
                    f"{self.volume_value}%",
                    font=self.font,
                    fill="white",
                )

            if self.audio_menu_selection == 2:
                current_device = self.audio_output_options[self.audio_output_selection]
                draw.text(
                    (60, 30 + 24), f"< {current_device} >", font=self.font, fill="white"
                )

        self._safe_draw(draw_callback)

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
        """Update the display based on current menu state."""
        if self.current_menu == "main":
            self.display_menu()
        elif self.current_menu == "yes_no":
            self.display_yes_no_menu()
        elif self.current_menu == "files" and self.file_options:
            self.display_file_menu(self.file_options)
        elif self.current_menu == "currently_playing":
            current = (
                self.get_current_audio() if hasattr(self, "get_current_audio") else None
            )
            self.display_current_audio(current)
        elif self.current_menu == "audio_output":
            self.display_audio_output_menu()
        elif self.current_menu == "audio_menu":
            self.display_audio_menu()

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
        while not confirmed:
            if timeout and (time.time() - start_time > timeout):
                logger.debug("Confirmation wait timed out")
                return False
            
            with self.lock:
                if self.option_confirmed:
                    confirmed = True
            
            if not confirmed:
                time.sleep(0.05)
                
        logger.debug("Received confirmation")
        return True
