import os
from pathlib import Path
import win32com.client # or comtypes

ppt_a = Path('submission/第6组_课程交付材料_20261108/第6组项目汇报PPT.pptx').resolve()
ppt_b = Path('runtime/第6组_pptmaster重排_20261108/exports/第6组_pptmaster重排_20261108_235451_native_charts_tables.pptx').resolve()

out_a = Path('runtime/preview_ppt_a').resolve()
out_b = Path('runtime/preview_ppt_b').resolve()
out_a.mkdir(parents=True, exist_ok=True)
out_b.mkdir(parents=True, exist_ok=True)

import win32com.client
powerpoint = win32com.client.Dispatch("PowerPoint.Application")
try:
    deck_a = powerpoint.Presentations.Open(str(ppt_a), True, False, False)
    deck_a.SaveAs(str(out_a), 17) # ppSaveAsPNG
    deck_a.Close()
    print("Exported PPT A (current delivery)")

    deck_b = powerpoint.Presentations.Open(str(ppt_b), True, False, False)
    deck_b.SaveAs(str(out_b), 17)
    deck_b.Close()
    print("Exported PPT B (pptmaster export)")
finally:
    powerpoint.Quit()
