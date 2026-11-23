import time
from collections import deque
from dataclasses import dataclass
from typing import Optional
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

@dataclass
class GestureEvent:
    gesture_type: str  # "SWIPE_LEFT" atau "SWIPE_RIGHT"
    timestamp: float

class GestureService:
    def __init__(self, model_path: str = "assets/models/hand_landmarker.task"):
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=1,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.6,
            min_tracking_confidence=0.6
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)
        
        # Buffer riwayat posisi X (timestamp, x_norm)
        self.x_history = deque(maxlen=15)
        self.last_trigger_time = 0.0
        
        # Parameter kalibrasi swipe yang LEBIH SENSITIF
        self.SWIPE_DISTANCE_THRESHOLD = 0.16  
        self.MIN_GESTURE_DURATION = 0.08      
        self.MAX_GESTURE_DURATION = 1.20      
        self.GESTURE_COOLDOWN = 1.0           

    def process_frame(self, frame_bgr) -> tuple[any, bool, Optional[GestureEvent]]:
        """Memproses frame, menggambar landmark, dan mendeteksi swipe."""
        annotated_frame = frame_bgr.copy()
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        result = self.landmarker.detect(mp_image)
        hand_detected = False
        gesture_event = None
        now = time.time()

        if result.hand_landmarks:
            hand_detected = True
            landmarks = result.hand_landmarks[0]
            
            # Gambar titik landmark pada preview kamera
            h, w, _ = annotated_frame.shape
            for lm in landmarks:
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.circle(annotated_frame, (cx, cy), 4, (0, 210, 215), -1)

            # Gunakan landmark 0 (Wrist / pergelangan tangan) untuk tracking stabil
            wrist_x = landmarks[0].x
            self.x_history.append((now, wrist_x))
            
            gesture_event = self._evaluate_swipe(now)
        else:
            self.x_history.clear()

        return annotated_frame, hand_detected, gesture_event

    def _evaluate_swipe(self, now: float) -> Optional[GestureEvent]:
        if len(self.x_history) < 5:
            return None
        if (now - self.last_trigger_time) < self.GESTURE_COOLDOWN:
            return None

        start_time, start_x = self.x_history[0]
        end_time, end_x = self.x_history[-1]
        duration = end_time - start_time
        delta_x = end_x - start_x

        if self.MIN_GESTURE_DURATION <= duration <= self.MAX_GESTURE_DURATION:
            # Frame sudah di-mirror horizontal:
            # Tangan bergeser ke kiri layar -> delta_x negatif -> NEXT SLIDE
            if delta_x <= -self.SWIPE_DISTANCE_THRESHOLD:
                self.last_trigger_time = now
                self.x_history.clear()
                return GestureEvent("SWIPE_LEFT", now)
            # Tangan bergeser ke kanan layar -> delta_x positif -> PREV SLIDE
            elif delta_x >= self.SWIPE_DISTANCE_THRESHOLD:
                self.last_trigger_time = now
                self.x_history.clear()
                return GestureEvent("SWIPE_RIGHT", now)

        return None

    def close(self):
        self.landmarker.close()