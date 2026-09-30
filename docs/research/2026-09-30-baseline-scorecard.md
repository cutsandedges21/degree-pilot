# Baseline scorecard, 2026-09-30

The rule-based baseline (`--solver baseline`) on the first real test set. This is the bar
the model has to beat, and the fallback for any job where it doesn't.

## Test set

18 documents, all labelled from the source text (not from the baseline's drafts), all
passing `python -m model.eval.label check`.

| Family | Docs | Gold rows | Source |
|---|---|---|---|
| Transcript | 3 | 42 courses | Moss's Vanier transcript (local only), WSU high-school sample, a blank NYSED template (negative example) |
| Résumé | 7 | 44 activities + 96 bullets | 5 single résumés split out of the U of T Career Centre toolkit, Illinois (Mary Smith), Guelph-Humber CV |
| Syllabus | 8 | 39 deliverables | York University LA&PS course outlines |

J2: 86 items (42 courses, 44 activities), 150 gold tags. J3: 175 cases built from the J2
labels.

Dropped while building it: Queen's "Best Resumes" guide and the second Illinois résumé
(two-column layouts; see finding 4), and the second U of T toolkit (same people as the
first, so near-duplicates).

## Scorecard

```
J1 extract (18 docs, 221 gold rows)
  field           F1  95% CI             P     R  bar
  C.code        0.44  [0.00, 1.00]    1.00  0.29  MISS (bar 0.95)
  C.title       0.00  [0.00, 0.00]    0.00  0.00  MISS (bar 0.90)
  C.term        0.00  [0.00, 0.00]     —    0.00  MISS (bar 0.90)
  C.grade       0.00  [0.00, 0.00]     —    0.00  MISS (bar 0.95)
  C.credits     0.00  [0.00, 0.00]     —    0.00  MISS (bar 0.90)
  A.kind        0.53  [0.37, 0.69]    0.56  0.50  MISS (bar 0.90)
  A.title       0.53  [0.21, 0.82]    0.56  0.50  MISS (bar 0.90)
  A.org         0.44  [0.10, 0.67]    0.52  0.38  MISS (bar 0.90)
  A.dates       0.61  [0.34, 0.82]    0.64  0.58  MISS (bar 0.90)
  B.text        0.92  [0.87, 0.96]    0.92  0.92  ok (bar 0.90)
  D.name        0.33  [0.11, 0.61]    0.24  0.51  MISS (bar 0.90)
  D.weight      0.55  [0.41, 0.71]    0.40  0.85  MISS (bar 0.90)
  D.due         0.06  [0.00, 0.18]    0.07  0.06  MISS (bar 0.90)
  rows exactly right 108/221 · unparseable lines 0 · copy-rule breaks 0

J2 tag (9 docs, 86 items)
  precision 0.82 [0.71, 0.92] · recall 0.65 · F1 0.72 · bad tags 0 · ok (bar 0.80)

J3 explain (175 cases)
  pass rate 1.00 [1.00, 1.00] · facts used 4.1 on average · ok (bar 0.98)
```

## Findings

1. **Transcripts are where the baseline fails worst.** Omnivox (CEGEP) prints the term at
   the end of each course line (`… 78  74  2.00  A-25`, numbers made up); the baseline only knows terms as
   headers, so it stops at `A-25`, keeps the marks inside the title, and finds no grade,
   credits or term. The WSU transcript uses code-less course IDs (`ENGL1`) after a
   numeric state code, which the baseline doesn't recognize at all. Cheap baseline fixes
   before the app ships: trailing term tokens (`A-25`, `W-26`, `Fall 2025`) and a second
   code pattern.
2. **Syllabi: weights are found, names and dates aren't.** Recall on weights is 0.85, but
   every percentage in the policy text (late penalties, grade scales, "maximum of 70%")
   becomes a false deliverable (name precision 0.24). Due dates sit in separate table
   columns or lines, so the baseline almost never pairs them (0.06).
3. **Résumés: bullets are easy, headers are not.** Bullets score 0.92. Headers score about
   0.5 because schools order them differently (`Company, Title` vs `Title, Company`,
   headers split over two lines), and the baseline assumes one order.
4. **Two-column PDFs interleave.** pdf.js returns items by line across the whole page, so
   two columns (Queen's guide, the second Illinois résumé, WSU's side-by-side terms) come
   out interleaved line by line. Student résumés often use two-column templates. Before
   the app offers PDF import, `tools/pdftext/lines.mjs` needs column detection (split a
   page at a vertical gap that no line crosses); Phase 4's generators should then include
   two-column layouts.
5. **The test set is still small for transcripts and syllabi.** Transcripts have 42 rows
   from 3 documents and syllabi 39 rows from 8 (all York), both under the spec's 100. The
   `C.code` interval [0.00, 1.00] shows what three documents buy. Next: more transcripts
   (friends', with consent, kept local) and syllabi from other schools.
6. **J2 baseline sits right on its bar** (precision 0.82, interval 0.71–0.92), so a model
   has little room before it's worse than keywords. J3 templates pass by construction.

## Labelling conventions used

Recorded in `contracts/jobs.md` so the Phase 4 training data follows the same rules.
