import face_recognition
import cv2
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

class FaceService:
    def __init__(self, known_face_path="assets/faces/admin.jpg"):
        self.known_face_encodings = []
        self.is_ready = False
        
        # --- Fitur Grace Period (Toleransi Waktu) ---
        self.last_seen_time = 0.0
        self.grace_period = 3.5  # Berapa detik sistem tetap UNLOCKED setelah wajah tak terlihat
        
        # Load foto referensi
        if Path(known_face_path).exists():
            try:
                image = face_recognition.load_image_file(known_face_path)
                encoding = face_recognition.face_encodings(image)[0]
                self.known_face_encodings.append(encoding)
                self.is_ready = True
                logger.info("Foto referensi wajah (admin.jpg) berhasil dimuat!")
            except IndexError:
                logger.error("Tidak ada wajah yang terdeteksi di foto admin.jpg!")
        else:
            logger.error(f"File {known_face_path} tidak ditemukan!")

    def authenticate_frame(self, frame_bgr) -> bool:
        if not self.is_ready:
            return False

        now = time.time()

        # Perkecil ukuran frame menjadi 1/4 agar prosesnya sangat cepat (tidak lag)
        small_frame = cv2.resize(frame_bgr, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # Cari semua wajah di frame saat ini
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        # Cocokkan dengan wajah admin
        is_face_found_now = False
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.5)
            if True in matches:
                self.last_seen_time = now  # Catat waktu terakhir admin terlihat!
                is_face_found_now = True
                break

        # Jika wajah dikenali detik ini, kembalikan True
        if is_face_found_now:
            return True

        # Jika wajah tidak terlihat, cek apakah masih dalam batas waktu toleransi
        if (now - self.last_seen_time) < self.grace_period:
            return True # Tahan status UNLOCKED!

        # Jika sudah lewat batas toleransi (3.5 detik) dan wajah tidak ada, baru kunci sistem
        return False