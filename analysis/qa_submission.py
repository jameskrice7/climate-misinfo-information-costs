"""Check PDF text, numerical provenance, and render all deliverables for review."""
from pathlib import Path
import json
import re
import shutil
import subprocess
from pypdf import PdfReader
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
SUB=ROOT/'paper/submission'; QA=SUB/'qa';QA.mkdir(exist_ok=True)
poppler=shutil.which('pdftoppm')
if not poppler:
    candidate=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
    if candidate.is_file():poppler=str(candidate)
if not poppler: raise FileNotFoundError('pdftoppm is required for visual QA')
report={}
for file in sorted(SUB.glob('*.pdf')):
    reader=PdfReader(file);text='\n'.join(p.extract_text() or '' for p in reader.pages)
    if 'Anonymous' in file.name:
        assert not re.search(r'ricejames|0000-0001-9961|jameskrice7|James Rice',text,re.I),file
        assert not re.search(r'previous (draft|version)|earlier (draft|version)|revised draft|GPU|this machine',text,re.I),file
    assert not re.search(r'\?\?',text),f'Unresolved reference in {file}'
    assert not re.search(r'\bnan\b',text,re.I),f'Undefined numerical output in {file}'
    dest=QA/file.stem;dest.mkdir(exist_ok=True)
    for pattern in ['page-*.png','contact-*.png']:
        for old in dest.glob(pattern): old.unlink()
    subprocess.run([poppler,'-r','75','-png',str(file),str(dest/'page')],check=True,capture_output=True)
    paths=sorted(dest.glob('page-*.png'))
    for start in range(0,len(paths),6):
        canvas=Image.new('RGB',(1280,1734),'#dddddd'); draw=ImageDraw.Draw(canvas)
        for j,path in enumerate(paths[start:start+6]):
            im=Image.open(path).convert('RGB');im.thumbnail((620,816))
            x=(j%2)*640;y=(j//2)*578
            # Thumbnail scales to three rows of landscape monitor review.
            im.thumbnail((620,550));canvas.paste(im,(x+(640-im.width)//2,y+24))
            draw.text((x+10,y+5),f'{file.stem} page {start+j+1}',fill='black')
        canvas.save(dest/f'contact-{start//6+1}.png')
    report[file.name]={'pages':len(reader.pages),'bytes':file.stat().st_size,
      'text_characters':len(text),'metadata':{str(k):str(v) for k,v in (reader.metadata or {}).items()}}
    (dest/'text.txt').write_text(text,encoding='utf-8')
(QA/'automated_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
