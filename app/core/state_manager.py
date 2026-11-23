import logging
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

        # Final Security Gate: Periksa tepat sebelum eksekusi perintah
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
                try: pyautogui.press("right")
                except Exception as e: logger.error(f"Keyboard error: {e}")
            
    def prev_slide(self, trigger_keyboard: bool = False):
        if self.current_index > 1:
            self.current_index -= 1
            self._emit_slide_update()
            if trigger_keyboard:
                try: pyautogui.press("left")
                except Exception as e: logger.error(f"Keyboard error: {e}")
            
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