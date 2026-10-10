# Change log

Every change to this project is recorded here, newest day last. Each entry says what changed and why. Design decisions are marked **Decision**; the options and full reasoning for each are in [decision.md](decision.md).

## 2026-10-11

### Repository setup

- Cloned `Induseuro-labs/intern-assignment` into this folder. It contains only `README.md` and the two prompts in `questions/`; there is no starter code and no test images.
- Forked the repository to `prayag-1771/intern-assignment`. Remotes: `origin` is the fork, `upstream` is the original.
- Created the branch `solution` from `main`. All work happens here; submission will be a pull request from the fork to `upstream` `main`.

### Files added

- `.gitignore`: ignores `.env`, the virtual environment, Python caches and editor folders, so secrets and generated files are never committed.
- `.env` (not tracked): holds `GROQ_API_KEY` and `GEMINI_API_KEY`. Both keys were checked against their services and accepted.
- `.env.example`: a template with the two key names and no values, so someone else can see what to fill in.
- `requirement.md`: both questions restated in plain terms, with the hard parts, test data and scenarios.
- `log.md`: this file.

### Plan

- **Decision:** do Question 2 first, then Question 1. Only one question is required, and Question 2 has its full test data in the prompt, so finishing it first guarantees a complete submission.
- Target: Question 2 on days 1–2, Question 1 on days 3–4, with four days in total.

### Question 2: first experiment

- Embedded the ten test questions with Gemini's `gemini-embedding-001` model (3,072 numbers per question) and compared every pair by cosine similarity. This was a throwaway script; no project code exists yet.
- Result: true duplicates score 0.97–1.00, different questions score 0.81–0.93, and the ambiguous Q8 scores 0.92–0.94 against the Q1 group. Q6 and Q7 (both "different") score 0.93 against each other, in the same range as Q8.
- Meaning: similarity separates the clear cases, but a grey zone around 0.92–0.96 cannot be settled by a cut-off alone.
- **Decision:** the duplicate detector will be layered. Text matching catches exact copies, embeddings settle the clear cases, and an LLM judges only the grey-zone pairs. Chosen over "embeddings only" (would leave Q6/Q7 unresolved) and "LLM judges everything" (too slow and costly at thousands of questions).

### Working rules

- Every change is recorded in this file in the same step as the change.
- Each meaningful change gets its own commit on `solution`, authored only by `prayag-1771` with no co-author line.
- Commits stay local for now. The fork is public, so pushing waits until the work is ready to submit.

### Commits

- `Add gitignore and env template`: `.gitignore` and `.env.example`.
- `Add plain-terms requirements and change log`: `requirement.md` and `log.md`.

### Decision record

- Added `decision.md`. It lists every decision with all the options that were considered, ranked best to worst, the one chosen, and why. Backfilled with the three decisions made so far: D1 (fork), D2 (both questions, Question 2 first) and D3 (layered detector).
- From now on each new decision is added there in full, with a one-line note here.
- Commit: `Add decision record`.

### Open

- Next decision (D4): where the embeddings come from (a model run locally, or an online service).
- No project code has been written yet, and nothing has been pushed.
