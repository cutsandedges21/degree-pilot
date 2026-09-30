# Phase 1 review, 2026-09-30

Task 24 of the Phase 1 plan. A correctness review ran as a read-only agent; the premortem
agent lost its API connection mid-reply and hung, so the premortem below was written by
the main session instead.

## Correctness: 8 findings, all fixed in `bf4c2ec`

| Severity | Finding | Fix |
|---|---|---|
| High | Tool names and quotes were substring matches: "Git" passed inside "Digital", "Excel" inside "Excellence" | Whole-word matching (`contains_words`) |
| High | J3 accepted invented numbers hiding inside fact numbers ("2" and "5" inside "STAT 250") | Numbers compared as whole tokens |
| Medium | The copy rule matched short values anywhere: grade "A" was "found" in the word "a" | Whole tokens; values of 3 characters or fewer keep their case |
| Medium | Activity skill tags without a quote passed, as did one-letter quotes | Activities need a quote of 2+ characters |
| Medium | An item with no citable text crashed J3 case building | Such items are skipped |
| Medium | One bad gold.j1 aborted the scorecard with a bare traceback | The error names the file |
| Low | Parsers split on U+2028 and form feeds, which the formatter allowed inside values | Parsers split on `\n` only |
| Low | parse_facts allowed style last and evidence before any skill | Both rejected |

## Premortem: Phase 4's training data failed. Why?

1. **The decoder and the checks disagree on "verbatim".** J1 relies on constrained
   decoding that only emits text copied from the input. If the decoder's notion of a copy
   (tokens) differs from `contains_words` (normalized whole words), generated targets pass
   the check but the decoder can't produce them, or the reverse. *Before Phase 4:* build
   the constraint on the same normalization and test both on the same fixtures.
2. **Real PDFs don't look like the generated ones.** Two of 20 collected documents were
   unusable because pdf.js interleaves two-column pages, and the WSU transcript still is.
   A model trained on clean single-column text will fail on them. *Before Phase 4:* make
   `lines.mjs` column-aware, then have the generators render two-column layouts too.
3. **The test set can't tell a model from the baseline on courses.** Three transcripts
   (one a blank template) give `C.code` an interval of [0.00, 1.00]; all eight syllabi
   are from one university. *Before Phase 4's scorecard:* at least 10 transcripts in 4+
   layouts and 15 syllabi from 4+ schools.
4. **Labels are partly judgment calls.** J2 tags (is Mechanics also lab work?) and some J1
   kinds (club or volunteer?) were decided by one labeller. A model trained on generator
   conventions can lose precision for reasons unrelated to quality. *Before Phase 4:*
   generators follow `contracts/jobs.md` exactly, and a second labeller (Moss) re-tags 20
   items to measure agreement, which is the real ceiling for J2.
5. **J3's fact check has word-shaped holes.** It checks digits, codes, grades and skill
   names, so "two courses" or a synonym for a skill slips through. *Before Phase 4:* check
   number words (one to twenty) and add skill synonyms to the taxonomy.
