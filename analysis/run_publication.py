"""One-command CPU replication of all submitted regressions and figures.

Use --compile to build PDFs as well (requires pdflatex and bibtex on PATH).
The classifier is never run. Execute from any working directory.
"""
from pathlib import Path
import argparse
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--compile',action='store_true')
    ap.add_argument('--compile-only',action='store_true')
    args=ap.parse_args()
    if not args.compile_only:
        for name in ['audit_publication.py','publication_analysis.py','make_validation_sample.py',
                     'build_publication.py','test_publication.py']:
            subprocess.run([sys.executable,str(ROOT/'analysis'/name)],cwd=ROOT,check=True)
    if args.compile or args.compile_only:
        src=ROOT/'paper/submission/source'
        for name in ['main','supplement','title_page','cover_letter','declaration','author_manuscript']:
            for iteration in range(3):
                subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error',name+'.tex'],cwd=src,check=True)
                if iteration==0 and name in ['main','author_manuscript']:
                    subprocess.run(['bibtex',name],cwd=src,check=True)
        import shutil
        names={'main':'Manuscript_Anonymous','supplement':'Supplement_Anonymous',
               'title_page':'Title_Page','cover_letter':'Cover_Letter','declaration':'Competing_Interests'}
        for srcname,dest in names.items():shutil.copy2(src/(srcname+'.pdf'),src.parent/(dest+'.pdf'))
        shutil.copy2(src/'author_manuscript.pdf',ROOT/'paper/Rice_2026_Information_Costs_of_Climate_Misinformation.pdf')

if __name__=='__main__':main()
