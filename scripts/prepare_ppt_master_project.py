import shutil
import os
from pathlib import Path

proj = Path('projects/group6_defense_ppt169_20261108')
imported = proj / 'imported_svg'
svg_out = proj / 'svg_output'
svg_out.mkdir(parents=True, exist_ok=True)

# Copy svgs
count = 0
for f in (imported / 'svg-flat').glob('*.svg'):
    shutil.copy2(f, svg_out / f.name)
    count += 1
print(f'Copied {count} SVGs to {svg_out}')

# Copy images
images_dir = proj / 'images'
if not images_dir.exists():
    shutil.copytree(imported / 'images', images_dir)
print(f'Images copied to {images_dir}')

# Copy notes
notes_dir = proj / 'notes'
if not notes_dir.exists():
    shutil.copytree(imported / 'notes', notes_dir)
print(f'Notes copied to {notes_dir}')
