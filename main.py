import sys
import logging
from PySide6.QtWidgets import QApplication
from app.core.state_manager import StateManager
from app.ui.main_window import DashboardWindow

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    setup_logging()
    app = QApplication(sys.argv)
    
    # 1. Inisialisasi State
    state_manager = StateManager()
    
    # 2. Load file presentasi asli (Buat file presentasi.pptx di folder yang sama)
    # Anda bisa mengganti nama file ini dengan presentasi Anda sendiri
    pptx_file = "presentasi.pptx" 
    state_manager.load_presentation(pptx_file)
    
    # 3. Inisialisasi UI
    window = DashboardWindow(state_manager)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()