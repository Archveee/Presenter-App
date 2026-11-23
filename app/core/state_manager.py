import logging
import subprocess
import shutil
import time
import pyautogui
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from app.models.slide_info import SlideInfo
from app.core.pptx_parser import PPTXParser
from app.services.gesture_service import GestureEvent

logger = logging.getLogger(__name__)

class StateManager(QObject):
    security_status_changed = Signal(str)  # LOCKED, VERIFYING, UNLOCKED, CAMERA_LOST
    slide_changed = Signal(SlideInfo, SlideInfo)
    presentation_loaded = Signal(str)
    gesture_feedback = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.security_state = "LOCKED"
        self.gesture_enabled = True
        self.current_index = 1
        self.slides = []
        self.total_slides = 0
        # Class resmi milik aplikasi desktop OnlyOffice di Arch Linux
        self.target_window_class = "DesktopEditors"
        
    def load_presentation(self, file_path: str):
        path_obj = Path(file_path)
        if not path_obj.exists():
            logger.error(f"File tidak ditemukan: {file_path}")
            return
        self.slides = PPTXParser.parse(str(path_obj))
        self.total_slides = len(self.slides)
        self.current_index = 1
        self.presentation_loaded.emit(path_obj.name)
        if self.total_slides > 0:
            self._emit_slide_update()

    def set_security_state(self, new_state: str):
        if self.security_state != new_state:
            self.security_state = new_state
            logger.info(f"Security State -> {new_state}")
            self.security_status_changed.emit(new_state)
            
    def handle_face_auth(self, is_authenticated: bool):
        if self.security_state == "CAMERA_LOST":
            return
        new_state = "UNLOCKED" if is_authenticated else "LOCKED"
        self.set_security_state(new_state)

    def handle_camera_status(self, status: str):
        if "ERROR" in status or "LOST" in status or "DISCONNECTED" in status:
            self.set_security_state("CAMERA_LOST")
        elif self.security_state == "CAMERA_LOST" and status == "CONNECTED":
            self.set_security_state("LOCKED")

    def toggle_gesture_control(self):
        self.gesture_enabled = not self.gesture_enabled
        state_str = "ENABLED" if self.gesture_enabled else "PAUSED"
        self.gesture_feedback.emit(f"Gesture Control: {state_str}")

    def handle_gesture(self, event: GestureEvent):
        if not self.gesture_enabled:
            self.gesture_feedback.emit("IGNORED - Gesture Paused")
            return

        if self.security_state != "UNLOCKED":
            self.gesture_feedback.emit(f"BLOCKED ({event.gesture_type}) - {self.security_state}")
            return

        if event.gesture_type == "SWIPE_LEFT":
            self.gesture_feedback.emit("SWIPE LEFT -> NEXT SLIDE")
            self.next_slide(trigger_keyboard=True)
        elif event.gesture_type == "SWIPE_RIGHT":
            self.gesture_feedback.emit("SWIPE RIGHT -> PREV SLIDE")
            self.prev_slide(trigger_keyboard=True)
            
    def next_slide(self, trigger_keyboard: bool = False):
        if self.current_index < self.total_slides:
            self.current_index += 1
            self._emit_slide_update()
            if trigger_keyboard:
                self._send_presentation_key("right")
            
    def prev_slide(self, trigger_keyboard: bool = False):
        if self.current_index > 1:
            self.current_index -= 1
            self._emit_slide_update()
            if trigger_keyboard:
                self._send_presentation_key("left")

    def _send_presentation_key(self, direction: str):
        """Cari jendela slideshow berdasarkan class DesktopEditors, tekan panah, lalu kembali ke Dashboard."""
        try:
            key_name = "Right" if direction == "right" else "Left"
            
            if shutil.which("xdotool"):
                # 1. Cari semua jendela milik OnlyOffice berdasarkan --class (menangkap editor & layar slideshow)
                win_ids = subprocess.check_output(
                    ["xdotool", "search", "--onlyvisible", "--class", self.target_window_class],
                    timeout=1
                ).decode().splitlines()
                
                if win_ids:
                    # Jendela slideshow fullscreen selalu berada di urutan teratas (indeks terakhir)
                    slideshow_id = win_ids[-1]
                    subprocess.run(
                        ["xdotool", "windowactivate", "--sync", slideshow_id],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1
                    )
                    time.sleep(0.08)
                    subprocess.run(
                        ["xdotool", "key", "--clearmodifiers", key_name],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1
                    )
                    time.sleep(0.08)
                else:
                    logger.warning("Jendela OnlyOffice (DesktopEditors) tidak ditemukan!")

                # 2. Kembalikan fokus & raise jendela AI Presenter Control
                ai_ids = subprocess.check_output(
                    ["xdotool", "search", "--onlyvisible", "--name", "AI Presenter Control"],
                    timeout=1
                ).decode().splitlines()
                
                if ai_ids:
                    subprocess.run(
                        ["xdotool", "windowactivate", ai_ids[-1]],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1
                    )
            else:
                pyautogui.press(direction)

            # 3. Kunci kembali status Always-on-Top
            if shutil.which("wmctrl"):
                subprocess.Popen(
                    ["wmctrl", "-r", "AI Presenter Control", "-b", "add,above"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                
            logger.info(f"Tombol '{direction}' dikirim ke slideshow OnlyOffice")
        except Exception as e:
            logger.error(f"Gagal mengirim input keyboard: {e}")
            
    def _emit_slide_update(self):
        if not self.slides:
            return
        current = self.slides[self.current_index - 1]
        next_slide = (
            self.slides[self.current_index] 
            if self.current_index < self.total_slides 
            else SlideInfo(0, "End of Presentation", [])
        )
        self.slide_changed.emit(current, next_slide)