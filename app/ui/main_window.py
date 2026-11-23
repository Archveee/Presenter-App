import pathlib
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QFrame, QSplitter, QGridLayout, QFileDialog)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QKeySequence, QShortcut
from app.core.state_manager import StateManager
from app.workers.camera_worker import CameraWorker

class DashboardWindow(QMainWindow):
    def __init__(self, state_manager: StateManager):
        super().__init__()
        self.state = state_manager
        self.setWindowTitle("AI Presenter Control")
        self.setMinimumSize(1240, 820)
        
        style_path = pathlib.Path(__file__).parent / "styles" / "dark_theme.qss"
        if style_path.exists():
            with open(style_path, "r") as f:
                self.setStyleSheet(f.read())

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 1. Top Header
        header_layout = QHBoxLayout()
        title = QLabel("AI PRESENTER CONTROL")
        title.setProperty("class", "HeaderLabel")
        
        self.lbl_filename = QLabel("No File Loaded")
        self.lbl_filename.setStyleSheet("color: #8D99AE; font-weight: bold; margin-left: 15px;")
        
        btn_open_pptx = QPushButton("📂 Open PPTX")
        btn_open_pptx.clicked.connect(self.open_presentation_dialog)
        
        header_layout.addWidget(title)
        header_layout.addWidget(self.lbl_filename)
        header_layout.addStretch()
        header_layout.addWidget(btn_open_pptx)
        main_layout.addLayout(header_layout)

        # 2. Main Content Splitter
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, 1)

        # Left Panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.security_card = self._create_card("FACE AUTHENTICATION", self._create_security_content())
        self.camera_card = self._create_card("CAMERA PREVIEW", self._create_camera_content())
        self.control_card = self._create_card("CONTROLS & SHORTCUTS", self._create_controls())
        
        left_layout.addWidget(self.security_card)
        left_layout.addWidget(self.camera_card, 1)
        left_layout.addWidget(self.control_card)
        splitter.addWidget(left_panel)

        # Center Panel (Slides + Thumbnails)
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        
        self.current_slide_card = self._create_card("CURRENT SLIDE", self._create_current_slide_widget())
        self.next_slide_card = self._create_card("NEXT SLIDE", self._create_next_slide_widget())
        
        center_layout.addWidget(self.current_slide_card, 2)
        center_layout.addWidget(self.next_slide_card, 1)
        splitter.addWidget(center_panel)

        # Right Panel (Speaker Notes)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.notes_label = QLabel("No speaker notes.")
        self.notes_label.setProperty("class", "NotesLabel")
        self.notes_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.notes_label.setWordWrap(True)
        self.notes_card = self._create_card("SPEAKER NOTES", self.notes_label)
        
        right_layout.addWidget(self.notes_card, 1)
        splitter.addWidget(right_panel)
        splitter.setSizes([340, 480, 420])

        # Keyboard Shortcuts untuk kontrol manual cepat
        QShortcut(QKeySequence(Qt.Key_Right), self, lambda: self.state.next_slide(trigger_keyboard=False))
        QShortcut(QKeySequence(Qt.Key_Left), self, lambda: self.state.prev_slide(trigger_keyboard=False))

        # Connect State Signals
        self.state.security_status_changed.connect(self.update_security_ui)
        self.state.slide_changed.connect(self.update_slide_ui)
        self.state.gesture_feedback.connect(self.update_gesture_feedback)
        self.state.presentation_loaded.connect(lambda name: self.lbl_filename.setText(f"📄 {name}"))

        if self.state.total_slides > 0:
            self.state._emit_slide_update()

        # Start Camera Worker
        self.camera_worker = CameraWorker(camera_index=0)
        self.camera_worker.frame_ready.connect(self.update_camera_frame)
        self.camera_worker.camera_status.connect(self.update_camera_status)
        self.camera_worker.camera_status.connect(self.state.handle_camera_status)
        self.camera_worker.gesture_detected.connect(self.state.handle_gesture)
        self.camera_worker.face_authenticated.connect(self.state.handle_face_auth)
        self.camera_worker.start()

    def _create_card(self, title: str, content_widget: QWidget) -> QFrame:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        header = QLabel(title)
        header.setProperty("class", "HeaderLabel")
        layout.addWidget(header)
        layout.addWidget(content_widget)
        return frame

    def _create_security_content(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        self.lbl_security_status = QLabel("LOCKED")
        self.lbl_security_status.setProperty("class", "SecurityLocked")
        self.lbl_security_desc = QLabel("Presenter not authenticated.")
        layout.addWidget(self.lbl_security_status)
        layout.addWidget(self.lbl_security_desc)
        return container

    def _create_camera_content(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        self.lbl_camera_feed = QLabel("Initializing Camera...")
        self.lbl_camera_feed.setAlignment(Qt.AlignCenter)
        self.lbl_camera_feed.setMinimumHeight(200)
        self.lbl_camera_feed.setStyleSheet("background-color: #181B20; border-radius: 6px;")
        self.lbl_camera_status = QLabel("Status: Starting...")
        self.lbl_gesture_status = QLabel("Gesture: Waiting...")
        layout.addWidget(self.lbl_camera_feed, 1)
        layout.addWidget(self.lbl_camera_status)
        layout.addWidget(self.lbl_gesture_status)
        return container

    def _create_current_slide_widget(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        self.lbl_current_thumb = QLabel()
        self.lbl_current_thumb.setAlignment(Qt.AlignCenter)
        self.lbl_current_thumb.setMinimumHeight(220)
        self.lbl_current_thumb.setStyleSheet("background-color: #181B20; border-radius: 6px;")
        self.current_slide_label = QLabel("No Presentation Loaded")
        self.current_slide_label.setProperty("class", "TitleLabel")
        self.current_slide_label.setWordWrap(True)
        layout.addWidget(self.lbl_current_thumb, 1)
        layout.addWidget(self.current_slide_label)
        return container

    def _create_next_slide_widget(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        self.lbl_next_thumb = QLabel()
        self.lbl_next_thumb.setAlignment(Qt.AlignCenter)
        self.lbl_next_thumb.setFixedSize(160, 100)
        self.lbl_next_thumb.setStyleSheet("background-color: #181B20; border-radius: 6px;")
        self.next_slide_label = QLabel("-")
        self.next_slide_label.setWordWrap(True)
        layout.addWidget(self.lbl_next_thumb)
        layout.addWidget(self.next_slide_label, 1)
        return container
        
    def _create_controls(self) -> QWidget:
        container = QWidget()
        layout = QGridLayout(container)
        btn_prev = QPushButton("◄ Prev Slide")
        btn_next = QPushButton("Next Slide ►")
        self.btn_toggle_gesture = QPushButton("Pause Gesture AI")
        
        btn_prev.clicked.connect(lambda: self.state.prev_slide(trigger_keyboard=False))
        btn_next.clicked.connect(lambda: self.state.next_slide(trigger_keyboard=False))
        self.btn_toggle_gesture.clicked.connect(self._on_toggle_gesture)
        
        layout.addWidget(btn_prev, 0, 0)
        layout.addWidget(btn_next, 0, 1)
        layout.addWidget(self.btn_toggle_gesture, 1, 0, 1, 2)
        return container

    def _on_toggle_gesture(self):
        self.state.toggle_gesture_control()
        self.btn_toggle_gesture.setText(
            "Pause Gesture AI" if self.state.gesture_enabled else "Resume Gesture AI"
        )

    def open_presentation_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Pilih File Presentasi", "", "PowerPoint Files (*.pptx)"
        )
        if file_path:
            self.state.load_presentation(file_path)

    # --- UI Update Slots ---
    def update_camera_frame(self, qt_image: QImage):
        pixmap = QPixmap.fromImage(qt_image)
        scaled = pixmap.scaled(self.lbl_camera_feed.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.lbl_camera_feed.setPixmap(scaled)

    def update_camera_status(self, status: str):
        self.lbl_camera_status.setText(f"Camera: {status}")

    def update_gesture_feedback(self, text: str):
        self.lbl_gesture_status.setText(f"Event: {text}")

    def update_security_ui(self, status: str):
        self.lbl_security_status.setText(status)
        if status in ("LOCKED", "CAMERA_LOST"):
            self.lbl_security_status.setProperty("class", "SecurityLocked")
            desc = "Camera disconnected!" if status == "CAMERA_LOST" else "Gestures blocked. Admin face not detected."
            self.lbl_security_desc.setText(desc)
        else:
            self.lbl_security_status.setProperty("class", "SecurityUnlocked")
            self.lbl_security_desc.setText("Admin verified. Gestures active.")
        self.lbl_security_status.style().unpolish(self.lbl_security_status)
        self.lbl_security_status.style().polish(self.lbl_security_status)

    def update_slide_ui(self, current, next_slide):
        self.current_slide_label.setText(f"Slide {current.index}/{self.state.total_slides}: {current.title}")
        if current.image_path:
            pix = QPixmap(current.image_path)
            self.lbl_current_thumb.setPixmap(pix.scaled(self.lbl_current_thumb.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.lbl_current_thumb.clear()
            self.lbl_current_thumb.setText("[Text Preview Mode]")

        if next_slide.index == 0:
            self.next_slide_label.setText("End of Presentation")
            self.lbl_next_thumb.clear()
        else:
            self.next_slide_label.setText(f"Slide {next_slide.index}: {next_slide.title}")
            if next_slide.image_path:
                pix_next = QPixmap(next_slide.image_path)
                self.lbl_next_thumb.setPixmap(pix_next.scaled(self.lbl_next_thumb.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.lbl_next_thumb.clear()

        notes_text = "\n".join([f"• {note}" for note in current.notes])
        self.notes_label.setText(notes_text if notes_text else "No speaker notes available.")

    def closeEvent(self, event):
        if hasattr(self, 'camera_worker'):
            self.camera_worker.stop()
        event.accept()