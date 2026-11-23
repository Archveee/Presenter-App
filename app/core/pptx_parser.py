from pptx import Presentation
from app.models.slide_info import SlideInfo
from app.services.thumbnail_service import ThumbnailService

class PPTXParser:
    @staticmethod
    def parse(file_path: str) -> list[SlideInfo]:
        try:
            prs = Presentation(file_path)
            thumbnails = ThumbnailService.generate_thumbnails(file_path)
            slides_data = []
            
            for index, slide in enumerate(prs.slides, start=1):
                title = f"Slide {index}"
                if slide.shapes.title and slide.shapes.title.text:
                    title = slide.shapes.title.text

                notes = []
                if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                    notes_text = slide.notes_slide.notes_text_frame.text
                    if notes_text.strip():
                        notes = [n.strip() for n in notes_text.split('\n') if n.strip()]

                img_path = thumbnails[index - 1] if (index - 1) < len(thumbnails) else ""
                slides_data.append(SlideInfo(index=index, title=title, notes=notes, image_path=img_path))
            
            return slides_data
        except Exception as e:
            print(f"Error parsing PPTX: {e}")
            return []