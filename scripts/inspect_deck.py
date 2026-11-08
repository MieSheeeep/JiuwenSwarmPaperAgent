import pptx
import sys

file_path = sys.argv[1] if len(sys.argv) > 1 else "docs/第6组项目汇报PPT_终版.pptx"
prs = pptx.Presentation(file_path)
print(f"Presentation: {file_path}")
print(f"Slide count: {len(prs.slides)}")
for idx, slide in enumerate(prs.slides):
    notes = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""
    first_title = ""
    for shape in slide.shapes:
        if shape.has_text_frame and shape.text_frame.text.strip():
            first_title = shape.text_frame.text.splitlines()[0]
            break
    print(f"Slide {idx+1:02d}: {first_title[:45]} | Shapes: {len(slide.shapes)} | Notes len: {len(notes)} chars")
