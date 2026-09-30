# Job contracts

DegreePilot's model does three jobs. This file fixes the text each job reads and writes.
`model/jobs/` parses and checks these formats; the browser app will do the same.

The formats can change until Phase 4 generates training data from them. After that, a
change means regenerating the data and retraining.

## J1 extract

Reads a chunk of a transcript, résumé, syllabus or short note. Writes one record per
line, fields separated by ` | `.

| Record | Fields | Example |
|---|---|---|
| `C` course | code, title, term, grade, credits | `C \| ECON 201 \| Intermediate Microeconomics \| Fall 2025 \| A- \| 3.0` |
| `A` activity | kind, title, org, dates, role | `A \| club \| President \| Economics Society \| 2024–2025 \|` |
| `B` bullet | text, belonging to the activity above | `B \| Organized 6 speaker events for 120 members` |
| `D` deliverable | name, weight, due | `D \| Midterm exam \| 25% \| Oct 21` |

1. **Copy, don't rewrite.** Every value except an activity's kind appears in the input as
   written, after normalization (NFKC, casefolded, whitespace collapsed, edge punctuation
   trimmed, never `-` or `+`). `Oct 21` stays `Oct 21`; turning it into a date is code's job.
2. Any value may be empty. No value contains `|` or a line break.
3. `kind` is one of: job, internship, project, club, volunteer, award, research, sport, other.
4. When a course shows both a percent and a letter grade, the grade is the letter.
5. A term printed above a block of courses belongs to every course in the block.
6. A failed course (Omnivox `EC`) keeps its mark as the grade; its credits stay empty.
7. An activity's `title` is the position held, or the project or award name; `org` is
   where; `role` stays empty unless the entry names a separate role.
8. Not activities: summaries and skills lists, education entries (degree, GPA, coursework,
   a Dean's List line under a degree), certifications and trainings. Awards and honours
   are activities (kind `award`) wherever they appear.
9. A deliverable's `due` is the date its grading row gives. `TBA`, `TBD` or a period name
   ("Final Exam Period") stays empty. A deliverable repeated in a schedule is not a new one.
10. When a PDF splits a table cell across lines, copy the part that names the thing
    (`Group assignment`), since values must be verbatim.

## J2 tag

Reads one item: a `C` line, or an `A` line with its `B` lines. Writes what it shows:

    quantitative                 a skill id from contracts/skills.json
    leadership | President       a skill id with the input words that justify it
    tool | SQL                   a tool from the list in contracts/skills.json

1. Skill ids and tool names come from `contracts/skills.json` only.
2. Quotes and tool names appear in the item's text.
3. Courses need no quotes; activities quote their evidence.
4. A course gets the skills its title clearly implies; an activity gets the skills its
   words show. Leave a tag out when unsure: the bar is precision.

Gold files (`gold.j2`): each item's record lines, then its tags indented two spaces, a
blank line between items.

## J3 explain

Reads `key: value` facts and writes one to three plain sentences.

    style: why_fit
    career: Data Analyst
    skill: Quantitative reasoning (High)
    evidence: STAT 250 Introduction to Statistics, A
    evidence: ECON 301 Econometrics, A-

`style` comes first: `why_fit`, `gap` or `action`. Other keys: career, skill, evidence
(belongs to the skill above it), have, need, tool, action, because, effort.

`check_explanation` enforces:
1. Every course code, number, grade and skill name in the text appears in the facts.
2. The text uses at least two facts.

## Model framing (from Phase 2)

    <|job:extract|>transcript<|in|>…text…<|out|>…records…<|end|>
    <|job:tag|><|in|>…item…<|out|>…tags…<|end|>
    <|job:explain|><|in|>…facts…<|out|>…sentences…<|end|>
