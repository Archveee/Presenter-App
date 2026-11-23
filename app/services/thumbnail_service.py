import subprocess
import shutil
import hashlib
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

class ThumbnailService:
    # Gunakan absolute path agar PySide6 tidak bingung mencari file gambar
    CACHE_DIR = Path("assets/thumbnails").absolute()

    @classmethod
    def generate_thumbnails(cls, pptx_path: str) -> List[str]:
        """Merender thumbnail slide dari file PDF pendamping (hasil export OnlyOffice)."""
        source = Path(pptx_path).absolute()
        if not source.exists():
            logger.error(f"File PPTX tidak ditemukan: {source}")
            return []

        # Cari file PDF dengan nama sama di folder yang sama (.pdf atau .PDF)
        pdf_source = source.with_suffix(".pdf")
        if not pdf_source.exists():
            pdf_source = source.with_suffix(".PDF")
            if not pdf_source.exists():
                logger.warning(f"File PDF pendamping tidak ditemukan. Export dulu ke PDF: {source.with_suffix('.pdf').name}")
                return []

        if not shutil.which("pdftoppm"):
            logger.warning("pdftoppm tidak ditemukan. Jalankan: sudo pacman -S poppler")
            return []

        # Buat folder cache unik
        file_hash = hashlib.md5(f"{pdf_source.name}_{pdf_source.stat().st_mtime}".encode()).hexdigest()[:10]
        target_dir = cls.CACHE_DIR / file_hash
        target_dir.mkdir(parents=True, exist_ok=True)

        existing_pngs = sorted(target_dir.glob("slide-*.png"), key=lambda p: cls._extract_page_num(p.stem))
        if existing_pngs:
            logger.info(f"Memuat {len(existing_pngs)} thumbnail dari cache.")
            return [str(p.absolute()) for p in existing_pngs]

        try:
            logger.info(f"Mulai render PDF ke gambar: {pdf_source}")
            # DEVNULL dihapus agar error pdftoppm langsung tercetak merah di terminal
            subprocess.run(
                ["pdftoppm", "-png", "-r", "120", str(pdf_source), str(target_dir / "slide")],
                check=True
            )
            rendered_pngs = sorted(target_dir.glob("slide-*.png"), key=lambda p: cls._extract_page_num(p.stem))
            logger.info(f"Berhasil merender {len(rendered_pngs)} gambar slide.")
            return [str(p.absolute()) for p in rendered_pngs]
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Proses render GAGAL (pdftoppm error). Kode: {e.returncode}")
            return []
        except Exception as e:
            logger.error(f"Gagal memproses file: {e}")
            return []

    @staticmethod
    def _extract_page_num(stem: str) -> int:
        parts = stem.split("-")
        return int(parts[-1]) if parts[-1].isdigit() else 0