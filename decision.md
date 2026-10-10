# Decisions

Every design choice made on this project, in the order it was made. Each entry lists the options that were on the table, ranked from best to worst for this assignment, then the one chosen and why.

A short note of each decision also goes in [log.md](log.md); this file holds the full reasoning.

## D1. Where the solution lives

**Date:** 2026-10-11

**Question:** should the work go in a fork of the assignment repository or in a new repository?

| Rank | Option | For | Against |
|------|--------|-----|---------|
| 1 | Fork `Induseuro-labs/intern-assignment` | The only way to open a pull request against their repository, which is how the one existing submission was made. Keeps the prompts and history attached to the solution. | A fork of a public repository is always public, so other candidates can see what is pushed. |
| 2 | New private repository | Work stays hidden from other candidates. | Cannot open a pull request to their repository; the reviewers would need to be given access separately, and nothing in the README asks for that. |
| 3 | New public repository | Simple to create. | Public like a fork, but with no link to the assignment and no pull request. The drawbacks of both other options with none of the benefits. |

**Chosen:** option 1, the fork (`prayag-1771/intern-assignment`).

**Why:** the README does not say how to submit, and the only evidence is another candidate's pull request against the original repository. A fork is the only option that supports that. The visibility problem is handled by committing locally and pushing only when the work is ready.

## D2. Which question to do, and in what order

**Date:** 2026-10-11

**Question:** only one question is required and there are four days. Do one or both, and which first?

| Rank | Option | For | Against |
|------|--------|-----|---------|
| 1 | Both, Question 2 first | Question 2 has its full test data and expected answers in the prompt, so it can be built and proven quickly. Finishing it first guarantees a complete submission; Question 1 is then all upside. | Day 4 is tight for Question 1. |
| 2 | Question 2 only, polished | Safest. All four days go into one well-tested answer. | Leaves the larger question untouched when another candidate has attempted both. |
| 3 | Both, Question 1 first | Tackles the bigger question while fresh. | Question 1 has four connected parts and needs test images made first. If it overruns, there may be no finished question at all. |
| 4 | Question 1 only | Shows the widest range of skills in one answer. | Highest risk: the largest scope, the least-specified test data, and nothing to fall back on. |

**Chosen:** option 1, both questions with Question 2 first.

**Why:** it secures the minimum requirement early and still aims for both. If Question 1 runs over, its scope is cut (simpler layouts, no interface) and the finished Question 2 is not touched.

## D3. How the duplicate detector decides (Question 2)

**Date:** 2026-10-11

**Question:** how should the detector classify a new question against the stored ones, especially pairs that are close in wording but may or may not test the same thing?

**Evidence:** the ten test questions were embedded with Gemini's `gemini-embedding-001` and every pair compared by cosine similarity.

| Pair | Expected by the prompt | Similarity |
|------|------------------------|------------|
| Q1 vs Q2, Q3, Q4 | Semantic duplicates | 0.98 |
| Q2 vs Q10 | Exact duplicate | 1.00 |
| Q1 vs Q8 | Ambiguous, review | 0.94 |
| Q6 vs Q7 | Different | 0.93 |
| Q1 vs Q5 | Different | 0.91 |
| Q1 vs Q6, Q7, Q9 | Different | 0.83–0.88 |

True duplicates score 0.97 or higher and different questions 0.93 or lower, but Q8 (ambiguous) and Q6/Q7 (different) fall in the same narrow range. A cut-off alone cannot separate them.

| Rank | Option | For | Against |
|------|--------|-----|---------|
| 1 | Layered: text match, then embeddings, then an LLM judge for grey-zone pairs only | Each layer does what it is good at: text match is exact and free, embeddings are fast and settle the clear cases, and the LLM reasons about the few unclear pairs. Scales, because the LLM sees only a handful of pairs per new question. | More parts to build, test and explain. The LLM step needs a key and can vary between runs. |
| 2 | Embeddings only, with a "needs review" band | Simplest. Fast, runs fully offline, and gives the same answer every time. | Leaves Q6/Q7 flagged for review instead of classed as different, so a person has to resolve every grey-zone pair. |
| 3 | LLM judges every pair | The best judgement on any single pair. | One LLM call per stored question for each new question: slow and costly at thousands of questions, and answers can vary between runs. Fails the "how does it scale" requirement. |

**Chosen:** option 1, the layered detector.

**Why:** it is the only option that gets the grey-zone pairs right without sending every pair to an LLM. The extra parts are worth it because the prompt asks specifically about scale and about questions that are "effectively equivalent" despite different wording.

## Pending

- **D4.** Where the embeddings come from: a model run locally, or an online service.
