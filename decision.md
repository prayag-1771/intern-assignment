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

## D4. Detection design in detail (Question 2)

**Date:** 2026-10-11

**Question:** D3 chose a layered detector. Research turned up several ways to build one, plus the alternatives to it. Which exact design do we build?

**Evidence:** 36 sources were checked (papers, three patents, a Kaggle-winning solution and a deployed exam system); the full list is in [log.md](log.md). The findings that shaped this decision:

- Every field with this problem uses a cheap wide search followed by a careful judge on the few survivors: exam item banks ([Ma 2026](https://aclanthology.org/2026.aimecon-sessions.9.pdf)), record matching ([Peeters et al. 2025](https://arxiv.org/abs/2310.11244)), search ([Sentence Transformers](https://sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html)) and the [Kaggle Eedi winner](https://www.eedi.com/news/from-wrong-answers-to-real-insights-how-we-used-a-kaggle-challenge-to-map-student-misconceptions).
- The search stage can miss real duplicates. In Ma 2026 the same embedding search found 96.2% of known duplicate pairs on one exam and 47.3% on another, because some duplicates shared an answer but were worded differently. A second search route based on content tags fixed it.
- Showing the judge several candidates together works better than one pair at a time ([Wang et al. 2025](https://arxiv.org/abs/2405.16884)).
- One fixed similarity cut-off gives unpredictable error rates ([vCache](https://arxiv.org/abs/2502.03771)). Published pipelines use cut-offs anywhere from 0.85 to 0.99.
- In Ma 2026 a model change cut recall from 0.75 to 0.54, and a prompt rewrite raised it to 0.82. Four human experts on the same pairs ranged from 0.70 to 0.91 recall.

Options are ranked by accuracy first, then whether the approach scales, then build time.

| Rank | Option | For | Against |
|------|--------|-----|---------|
| 1 | Layered, two search routes: exact-text match, then the nearest few stored questions found two ways (by embedding and by a "concept tested" tag), then an LLM compares the new question with those few together against a written definition of "duplicate" | The most complete design. The tag route catches duplicates that are worded very differently, which is the failure Ma 2026 hit in production. | One LLM call per stored question to tag it. More parts to build and test. My estimate is about half a day more than option 2. |
| 2 | Layered, one search route: the same without tags | Strong and simpler. One LLM call per new question however large the bank. Same shape as the Kaggle Eedi winner and as the deployed system in Ma 2026 before its fix. | Blind to duplicates the embedding search does not rank among the nearest few. |
| 3 | Layered, with a small trained judge instead of the LLM (a model already trained on Quora's duplicate questions) | Runs offline and gives the same answer every time. The best models of this kind reach [92.7% accuracy](https://huggingface.co/microsoft/deberta-v2-xlarge) on Quora's own data. | It learned Quora's idea of "duplicate". It cannot be given our definition (same concept but a different task is not a duplicate) and cannot explain a verdict. |
| 4 | Embeddings with cut-offs only, grey zone left for a person | Simple, fast, offline. Common in dataset-building pipelines. | Leaves Q6/Q7 and Q8 unresolved, and a fixed cut-off is unreliable. |
| 5 | LLM compares the new question against every stored question | The best judgement on any single pair. | Thousands of LLM calls per new question. Fails the scaling requirement. |
| 6 | Word overlap only (normalised text, shared-word runs, ROUGE-L) | Catches copies and light edits for free. Used by [Self-Instruct](https://arxiv.org/abs/2212.10560) and the [Prometric patent](https://patents.google.com/patent/US20220415203A1/en). | Misses paraphrases, which the prompt requires. Useful only as the first layer. |
| 7 | Train our own classifier | Highest scores on the Quora benchmark come from trained models. | Needs hundreds of thousands of labelled pairs. We have ten questions and four days. |

**Chosen:** option 1, the two-route design, built in two steps: the one-route detector first, then the concept-tag route.

**Why:** it is the most complete design and the only one that covers duplicates worded very differently, which the prompt names ("effectively equivalent" questions). Building the one-route detector first means there is always a working, tested detector even if time runs short. The same tags can also feed the coverage summary for generation (D8), so the extra work is shared.

**Revision note:** the first choice on 2026-10-11 was option 2, with the tag route added only if measurements showed the search missing duplicates. It was changed the same day for three reasons. That trigger depends on the test set containing hard cases, and the ten given questions contain none, so the weakness would have stayed hidden. The prompt asks for differently-worded equivalents by name. And the tagging cost is shared with the generation side.

**Rules this decision sets for the build:**

- The labelled test set must include hard pairs that the ten given questions lack: equivalent questions worded very differently, and similar-looking questions that test different things.
- The search stage is reported with and without the tag route, so the value of the second route is measured and not assumed.
- The search stage is measured on its own: how many known duplicates appear among the nearest few.
- Cut-offs are calibrated on labelled pairs, not picked by eye, and a "needs review" band is kept.
- The judge works from a written definition of "duplicate" with worked examples, and returns a label, a short reason and a confidence.
- The judge model is fixed and run with no randomness, and a labelled test set is kept so any change can be re-checked.
- Results are reported as how many duplicates were found and how many flags were correct, not as one accuracy number.

## D5. How duplicates are avoided during generation (Question 2)

**Date:** 2026-10-11

**Question:** how should the generation workflow use the existing questions to steer the LLM toward new ones, without exceeding the context limit and in a way that scales?

**Evidence:**

- [Lingo and Chhajer 2026](https://arxiv.org/abs/2604.07147) rebuild the prompt each round from a memory of accepted items: the 10 most recent as exclusions, 5 from the most crowded areas, and a count per category. On exam questions the share of late items repeating early ones fell from 34.0% with plain prompting to 0.0%. Their conclusion: "Deduplication and prompt evolution are individually insufficient but jointly effective." In their ablation, filtering alone kept 9 distinct topic clusters against 18 for the full method. This is a preprint with small experiments.
- [Islam et al. 2026](https://arxiv.org/abs/2605.18824) put all previously accepted questions from the same chapter into the prompt with an instruction to avoid near-duplicates, then remove remaining pairs above 0.90 similarity.
- [League of LLMs](https://arxiv.org/abs/2507.22359) keeps an embedding memory of past questions, compares each new one with its nearest neighbours, and regenerates on a match.
- [SAND-Math](https://arxiv.org/abs/2507.20527) generates freely and filters afterwards; its semantic filter removed 7.3% of items.
- [Verbalized sampling](https://arxiv.org/abs/2510.01171) raises variety within a batch (1.6 to 2.1 times in creative writing) but takes no account of an existing collection.

| Rank | Option | For | Against |
|------|--------|-----|---------|
| 1 | Memory-guided loop: each round the prompt is rebuilt from the bank (a short coverage summary, the nearest existing questions marked "already asked", and the thinnest topics to aim at); new questions are screened and rejects are fed back | Best evidence. The prompt stays a fixed size as the bank grows, which answers the context-limit and scaling points directly. Tells the LLM both what to avoid and what is missing. | More parts to build. Its main source is a preprint. |
| 2 | Nearest-question exclusions: retrieve the most similar stored questions and tell the LLM to avoid them | Simple and satisfies the brief. Used in published pipelines. | The LLM sees what to avoid but not what is missing, so it tends to stay in the same area. |
| 3 | Generate freely, filter afterwards | Easiest. Scales well. | Does not use the existing collection to guide the LLM, which the brief requires. Wasteful, and filtering alone narrows variety. |
| 4 | Paste the whole bank into the prompt | Trivial for a tiny bank. | Breaks the context-limit requirement and costs more with every question added. |
| 5 | Sampling tricks only (more randomness, verbalized sampling) | More variety within one batch. | Blind to the bank. An add-on at most. |
| 6 | Fine-tune the generator | None for this assignment. | The bank changes constantly; no time or data. |

**Chosen:** option 1, the memory-guided loop, kept small.

**Why:** it is the only option that answers all three points the brief raises: how existing questions are selected within the context limit, how meaning-level repeats are avoided, and how the approach scales. Its screening step is separate from the independent detector of D4, which still checks every question on its own.

## D6. Where the embeddings come from (Question 2)

**Date:** 2026-10-11

**Question:** the search stage needs every question turned into a vector. Should that be done by a model on our own machine or by an online service?

**Evidence:** every pair of the ten assignment questions was scored with each option (`q2-duplicate-questions/experiments/compare_embeddings.py`; results in `experiments/results/embedding_comparison.json`). The gap is the lowest score among true duplicate pairs minus the highest score among different pairs; a wider positive gap leaves more room for a cut-off.

| Option | Type | Lowest duplicate | Highest different | Gap | Q8 (ambiguous) | Time for 10 questions |
|--------|------|------------------|-------------------|-----|----------------|-----------------------|
| TF-IDF on words | Conventional | 0.12 | 0.80 | -0.67 | 0.04–0.79 | Instant |
| TF-IDF on character n-grams | Conventional | 0.14 | 0.76 | -0.61 | 0.15–0.57 | Instant |
| all-MiniLM-L6-v2 (87 MB) | Local model | 0.88 | 0.85 | +0.03 | 0.80–0.86 | 0.4 s on GPU, 0.1 s on CPU |
| all-mpnet-base-v2 (418 MB) | Local model | 0.78 | 0.78 | +0.01 | 0.75–0.81 | 0.2 s on GPU |
| Qwen3-Embedding-0.6B (1.1 GB) | Local model | 0.86 | 0.85 | +0.01 | 0.83–0.91 | 0.3 s on GPU |
| Qwen3-Embedding-0.6B with a task instruction | Local model | 0.94 | 0.83 | +0.11 | 0.86–0.89 | 0.3 s on GPU, 25 s on CPU |
| gemini-embedding-001 | Online service | 0.97 | 0.93 | +0.03 | 0.92–0.94 | 13.6 s |

Other facts that weighed in: the online service needs one request per question (about 1.4 seconds each) and an API key; and on the same day `gemini-2.5-flash` returned "no longer available", which shows that online models can be withdrawn.

| Rank | Option | For | Against |
|------|--------|-----|---------|
| 1 | A local model is the engine; Gemini stays only in the comparison as a reference point | Free and offline after one download. Fastest (about 0.03 seconds per question on the GPU). A reviewer can run it with no key. The model file cannot be withdrawn. The best gap in the test came from a local model. | A download on first run (87 MB to 1.1 GB depending on the model). The strongest model tested is slow without a GPU (about 2.5 seconds per question on this CPU). |
| 2 | Local by default, Gemini switchable in the pipeline | Flexible: works on a machine with no room for a model. | Each embedding model needs its own calibrated cut-offs, so calibration and testing double for little gain. |
| 3 | Gemini's online embeddings are the engine | No download. Handles long text and many languages. | A key and internet for every question. About 40 times slower. Rate limits. Can be withdrawn. A reviewer without a key cannot run the search stage at all. |
| 4 | TF-IDF only | Instant, no model. | Ranks the pairs backwards (gap -0.67): word overlap is not meaning. Fails the paraphrase requirement. |

**Chosen:** option 1, a local model as the engine.

**Why:** it wins on cost, speed, offline use and control, and gives up nothing on quality in this test. Keeping Gemini only in the comparison still lets the write-up show how the local choice measures against a hosted model.

**Still open:** which local model. Ten questions are too few to choose it. It will be chosen on the larger labelled set that D4 requires, with smaller models trained on duplicate questions added to the comparison. The task instruction is kept as a candidate setting because it widened the gap from +0.01 to +0.11 on the same model.

## Pending

Decisions still to make, numbered as they are made:

- Exactly what counts as a duplicate, including questions that change only the numbers.
- Which local embedding model, chosen on the labelled set.
- Which LLM generates the questions, which one tags, and which one judges.
- How the coverage summary is built: by grouping embeddings, by the concept tags that D4 provides, or both.
- How questions and vectors are stored.
