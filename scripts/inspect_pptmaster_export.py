import pptx
import sys

sys.stdout.reconfigure(encoding='utf-8')
p = "runtime/第6组_pptmaster重排_20261108/exports/第6组_pptmaster重排_20261108_235451_native_charts_tables.pptx"
prs = pptx.Presentation(p)
print(f"Presentation: {p}")
print("Slide count:", len(prs.slides))
for i, slide in enumerate(prs.slides):
    shapes_info = []
    for s in slide.shapes:
        name = s.name
        stype = s.shape_type
        text = s.text_frame.text[:30].replace("\n", " ") if s.has_text_frame else ""
        has_chart = s.has_chart
        has_table = s.has_table
        shapes_info.append(f"{name}(type={stype}, chart={has_chart}, table={has_table}, text='{text}')")
    print(f"\n--- Slide {i+1} ---")
    for si in shapes_info:
        print(" ", si)
