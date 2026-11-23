import subprocess
import shutil
import hashlib
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

class ThumbnailService:
    CACHE_DIR = Path("assets/thumbnails")

    @classmethod
    def generate_thumbnails(cls, pptx_path: str) -> List[str]:
        """Merender thumbnail slide dari file PDF pendamping (hasil export OnlyOffice)."""
        source = Path(pptx_path)
        if not source.exists():
            return []

        # Cari file PDF dengan nama sama di folder yang sama (misal: presentasi.pdf)
        pdf_source = source.with_suffix(".pdf")
        if not pdf_source.exists():
            logger.warning(f"File PDF pendamping ({pdf_source.name}) tidak ditemukan. Export dulu dari OnlyOffice ke PDF.")
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
            return [str(p) for p in existing_pngs]

        try:
            subprocess.run(
                ["pdftoppm", "-png", "-r", "120", str(pdf_source), str(target_dir / "slide")],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            rendered_pngs = sorted(target_dir.glob("slide-*.png"), key=lambda p: cls._extract_page_num(p.stem))
            return [str(p) for p in rendered_pngs]
        except Exception as e:
            logger.error(f"Gagal merender PDF ke gambar: {e}")
            return []

    @staticmethod
    def _extract_page_num(stem: str) -> int:
        parts = stem.split("-")
        return int(parts[-1]) if parts[-1].isdigit() else 0