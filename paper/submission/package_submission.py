"""Package verified submission files; never submit to a journal or send mail."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

SUB=Path(__file__).resolve().parent
ROOT=SUB.parents[1]
SRC=SUB/'source'

def main():
    abstract=(SRC/'generated/abstract.tex').read_text(encoding='utf-8').strip().replace(r'\%','%').replace('--','–')
    abstract=abstract.replace('$','').replace(r'\,','').replace('{','').replace('}','')
    metadata={
      'journal':'Energy Economics','article_type':'Research article',
      'title':'The Information Costs of Climate Misinformation: Evidence from Global Financial Data',
      'author':{'given_name':'James','family_name':'Rice','affiliation':'Department of Government, University of Essex',
                'email':'ricejames0@gmail.com','orcid':'0000-0001-9961-3461'},
      'abstract':abstract,'abstract_words':len(abstract.split()),
      'keywords':['Climate Misinformation','Information Asymmetry','Market Microstructure',
                  'Environmental Communication','Politics and Governance','Corporate Responsibility'],
      'jel':['G12','G14','Q40','Q54'],
      'replication_url':'https://github.com/jameskrice7/climate-misinfo-information-costs',
      'prepared_on':'2026-10-23','submitted':False,
      'guide_verification':'Publisher scope, replication policy, highlights and AI guidance checked. Detailed journal guide returned HTTP 403; portal-specific requirements remain an author check.'}
    (SUB/'Submission_Metadata.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
    (SUB/'Data_Availability.txt').write_text(
      'The financial analysis, fixed classifier scores, input audits, tables, figures and manuscript source are available at '
      'https://github.com/jameskrice7/climate-misinfo-information-costs. '
      'Financial observations originate from licensed Refinitiv data. Raw Meta Content Library records and post text '
      'are access-controlled and are not redistributed. The distributed fixed financial panel and daily content index '
      'reproduce the completed financial robustness estimates. Supplied financial diagnostics, corpus summaries '
      'and network assets are retained in the manuscript source; regenerating platform-based summaries requires '
      'authorized underlying records. A post-ID/date crosswalk and original '
      'post context are required for alternative post-subset aggregation and independent human validation. '
      'The repository README identifies the supplied inputs, software requirements and one-command replication.\n',encoding='utf-8')
    # Ship the dependency closure of the final documents, keeping unused source
    # fragments out of the upload archive. The intact attachment is preserved
    # separately in paper/source/.
    source_files={SRC/name for name in ['main.tex','supplement.tex','author_manuscript.tex',
      'title_page.tex','cover_letter.tex','declaration.tex','references.bib','main.bbl','author_manuscript.bbl']}
    queue=[p for p in source_files if p.suffix=='.tex']
    while queue:
        file=queue.pop()
        text=file.read_text(encoding='utf-8')
        for kind,relative in re.findall(r'\\(input|includegraphics)(?:\[[^\]]*\])?\{([^}]+)\}',text):
            candidate=SRC/relative
            if kind=='input' and not candidate.suffix:candidate=candidate.with_suffix('.tex')
            if not candidate.is_file():candidate=SRC/'figures'/relative
            if not candidate.is_file():raise FileNotFoundError(candidate)
            if candidate not in source_files:
                source_files.add(candidate)
                if candidate.suffix=='.tex':queue.append(candidate)
    assert all((SRC/name).is_file() for name in ['main.tex','supplement.tex','references.bib','main.bbl'])
    with zipfile.ZipFile(SUB/'LaTeX_Source.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(source_files):z.write(p,p.relative_to(SRC).as_posix())
    files=['Manuscript_Anonymous.pdf','Supplement_Anonymous.pdf','Title_Page.pdf','Cover_Letter.pdf',
      'Competing_Interests.pdf','Highlights.docx','Highlights.txt','Submission_Metadata.json',
      'Data_Availability.txt','LaTeX_Source.zip','README.md']
    for name in files:assert (SUB/name).is_file(),name
    manifest={name:hashlib.sha256((SUB/name).read_bytes()).hexdigest() for name in files}
    (SUB/'SHA256SUMS.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    with zipfile.ZipFile(SUB/'Energy_Economics_Submission.zip','w',zipfile.ZIP_DEFLATED) as z:
        for name in files+['SHA256SUMS.json']:z.write(SUB/name,name)
    for name in ['LaTeX_Source.zip','Energy_Economics_Submission.zip']:
        with zipfile.ZipFile(SUB/name) as z:assert z.testzip() is None
    print('Verified source and submission ZIPs;',len(source_files),'editable source assets.')

if __name__=='__main__':main()
