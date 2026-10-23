# Energy Economics submission package

**Title:** The Information Costs of Climate Misinformation: Evidence from Global Financial Data

**Author:** James Rice, University of Essex

**Correspondence:** ricejames0@gmail.com

**Prepared:** 23 October 2026

## Upload files

| File | Purpose |
|---|---|
| `Manuscript_Anonymous.pdf` | Restored-format main manuscript, original literature and integrated appendix, with targeted empirical revisions |
| `Supplement_Anonymous.pdf` | Measurement details, inference, robustness tables and sector leave-out figure |
| `Title_Page.pdf` | Author details, funding, ethics, competing interests and repository link |
| `Cover_Letter.pdf` | Cover letter addressed to Energy Economics editors |
| `Competing_Interests.pdf` | Separate competing-interest declaration |
| `Highlights.docx` | Five editable highlights, each under 85 characters |
| `Highlights.txt` | Plain-text copy of the highlights |
| `Submission_Metadata.json` | Abstract, keywords, JEL codes and author information for copy/paste |
| `Data_Availability.txt` | Author-identified data/code availability statement |
| `LaTeX_Source.zip` | Editable main/supplement/supporting TeX, bibliography, BBL and figure assets |
| `Energy_Economics_Submission.zip` | Complete collection of upload files and source archive |

`source/main.tex` and `source/supplement.tex` are anonymous. `source/author_manuscript.tex` builds the identified public paper. The public paper PDF is also stored in the repository's `paper/` directory.

## Reproduce

From the repository root:

```sh
python -m pip install -r requirements-publication.txt
python analysis/run_publication.py --compile
```

This runs input audits, all financial models, annotation-sample selection, financial table/figure generation, targeted manuscript preparation, checks and PDF compilation. It does not run classification. Python 3.12, pinned dependencies, `pdflatex` and `biber` are required. The full analysis has already been completed and was not rerun for the editorial restoration.

For text/table revisions using only the saved estimates:

```sh
python analysis/prepare_manuscript_revision.py
python analysis/run_publication.py --compile-only
python paper/submission/package_submission.py
```

The attached source is preserved under `paper/source/`. The literature review is unchanged; the main text is approximately 97% of its original length and the integrated document is almost exactly the original length. `editorial_revision_checks.json` records these comparisons and verifies that the saved statistical results are unchanged. Original corpus descriptions, descriptive tables and network figures remain supplied source assets; this does not imply regeneration from access-controlled platform records.

`analysis/qa_submission.py` extracts and checks PDF text and renders pages with Poppler. `create_highlights.py` creates the editable highlights using python-docx. The highlights were visually checked using Microsoft Word's PDF export because the packaged LibreOffice renderer was unavailable on this host.

## Journal preparation basis

The package follows a conventional editable LaTeX, author-date, separate-title-page submission format, with an anonymous manuscript/supplement and five short editable highlights. The official publisher description identifies Energy Economics as an energy-economics and energy-finance journal and requires replicable econometric work:

- [Energy Economics scope and replication policy](https://shop.elsevier.com/journals/energy-economics/0140-9883)
- [Journal author-guide endpoint](https://www.sciencedirect.com/journal/energy-economics/publish/guide-for-authors)
- [Elsevier highlights guidance](https://www.elsevier.com/researcher/author/tools-and-resources/highlights)
- [Elsevier AI disclosure policy](https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals)

The detailed journal-specific guide returned HTTP 403 during preparation. Therefore live portal fields, any mandatory journal forms, current fees and any more specific length/format requirements were not independently verified. No fee or submission was initiated. The source remains fully editable to accommodate the portal's requirements.

## Author checks before submission

Confirm the funding/ethics/contact statements, absence of simultaneous consideration elsewhere, and any source-data redistribution conditions. Review the substantive conclusion and the AI disclosure and accept responsibility for the final submission. Supply any portal-specific forms if requested. These are final author and portal checks; the manuscript contains no draft/version or local-hardware discussion.

The substantive limitations are disclosed in the paper. In particular, independent human classifier validation, the post-date crosswalk for relevance-threshold reaggregation, and causal identification remain unavailable. See the repository-level `ANALYSIS_AUDIT.md` for the complete audit and explanation of the changed financial interpretation.
