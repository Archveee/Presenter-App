import time
import logging
import cv2
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
from app.services.gesture_service import GestureService, GestureEvent
from app.services.face_service import FaceService

logger = logging.getLogger(__name__)

class CameraWorker(QThread):
    frame_ready = Signal(QImage)
    camera_status = Signal(str)
    hand_status = Signal(bool)
    gesture_detected = Signal(GestureEvent)
    face_authenticated = Signal(bool) # Signal baru untuk status wajah

    def __init__(self, camera_index: int = 0):
        super().__init__()
        self.camera_index = camera_index
        self._running = False

    def run(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            logger.error("Gagal membuka webcam.")
            self.camera_status.emit("CAMERA ERROR")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        gesture_service = GestureService()
        face_service = FaceService() # Inisialisasi Face Recognition

        self._running = True
        self.camera_status.emit("CONNECTED")
        
        frame_counter = 0
        last_auth_status = False

        while self._running:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)

            # 1. Proses Gestur Tangan (Setiap frame)
            annotated_frame, hand_found, event = gesture_service.process_frame(frame)
            self.hand_status.emit(hand_found)
            if event:
                self.gesture_detected.emit(event)

            # 2. Proses Wajah (Setiap 10 frame sekali agar tidak lag)
            if frame_counter % 10 == 0:
                is_auth = face_service.authenticate_frame(frame)
                if is_auth != last_auth_status:
                    last_auth_status = is_auth
                    self.face_authenticated.emit(is_auth)
            
            frame_counter += 1

            # 3. Kirim gambar ke UI
            rgb_image = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
            self.frame_ready.emit(qt_image)

            time.sleep(0.03)

        gesture_service.close()
        cap.release()