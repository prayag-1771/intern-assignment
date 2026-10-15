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

## D7. The rule for calling two questions the same (Question 2)

**Date:** 2026-10-11

**Question:** what written rule decides whether two questions are the same? The LLM judge follows this rule and the test set is labelled with it, so every later measurement depends on it.

| Rank | Option | For | Against |
|------|--------|-----|---------|
| 1 | Perfect-answer test: two questions are the same if a perfect answer to one would earn full marks on the other. It is applied by comparing the concept (what the question is about) and the task (define, state, calculate, compare). | Gives the assignment's expected label for all ten test questions. Each verdict can be explained and checked. Close to the definition used for exam items in [Ma 2026](https://aclanthology.org/2026.aimecon-sessions.9.pdf): items that need the same knowledge to answer are duplicates, while the same knowledge with a different focus or outcome is not. | Needs judgement on vague questions, which is why a "needs review" label exists. |
| 2 | Same topic: two questions are the same if they are about the same concept, whatever the task | Simplest to state and apply. | Calls Q6/Q7 and Q1/Q5 the same, against the assignment's labels. |
| 3 | No written rule: rely on similarity scores and the LLM's own sense of "duplicate" | Nothing to write. | Results shift with the model and cannot be explained or checked. In Ma 2026 the written definition and examples moved recall more than the model did (0.54 to 0.82). |

**Chosen:** option 1, the perfect-answer test.

**Why:** it is the only rule that agrees with the assignment's own answer key and can be checked pair by pair.

**Joined questions (added 2026-10-11 at the user's suggestion):** a question made only by joining existing questions counts as the same as those questions. Example: "Define reflection of light and state its laws." is Q1 and Q5 joined. Perfect answers to Q1 and Q5, taken together, are a perfect answer to it with nothing missing and nothing extra, so it asks nothing new. It is labelled a semantic duplicate of both. The first draft of the answer key labelled it "needs review" because it had been compared with one question at a time; comparing it with both together settles it. Allowing such questions would also let the generator pad the bank by joining old questions, the same problem D8 closes for number swaps.

This differs from a question that asks for only part of an existing one, such as "What is the relation between the angle of incidence and the angle of reflection?" against Q5. A perfect answer to that does not fully answer Q5, so the two are not equal, and it stays "needs review".

**The labels this gives:**

| Label | Meaning | Example |
|-------|---------|---------|
| Exact duplicate | The same text once case, punctuation and spacing are ignored | Q10 and Q2 |
| Semantic duplicate | Different words or format, same concept and same task; or existing questions joined into one | Q2 and Q1 |
| Variant | Same concept and same task; only the numbers or names change (see D8) | The Q7 question with 45° in place of 30° |
| Different | A different concept, or the same concept with a different task | Q6 (define) and Q7 (calculate) |
| Needs review | One question is broader, narrower or vaguer than the other, so the answer depends on context (see D9) | Q8 "What is reflection?" against Q1 |

## D8. Questions that only change the numbers (Question 2)

**Date:** 2026-10-11

**Question:** a new question repeats an existing one with different values, for example "The angle of incidence is 45°. What is the angle of reflection?" when the 30° version exists. The assignment's test data has no such case. How is it treated?

| Rank | Option | For | Against |
|------|--------|-----|---------|
| 1 | Its own label, "variant". Not counted as a new question by default, with a setting that allows variants when a teacher wants practice sheets. | The detector reports exactly what it found. The policy (allow or not) stays separate from the detection. Stops the generator from padding the bank with number swaps. | One more label for the judge to get right. |
| 2 | Label it a semantic duplicate | Simple and strict. | The distinction is lost, and variants can never be allowed. |
| 3 | Send it to "needs review" | Safe. | Fills the review list with cases that have a clear answer. |
| 4 | Label it different, so it is accepted as new | Follows the perfect-answer test literally (the answers differ). | The generator can fill the bank by changing numbers, which is not "genuinely new". |

**Chosen:** option 1, the "variant" label, rejected by default.

**Why:** it keeps the bank free of number swaps without throwing away the information that a teacher may sometimes want them.

## D9. What happens to "not sure" questions (Question 2)

**Date:** 2026-10-11

**Question:** when the detector labels a question "needs review", is it let into the bank or not?

| Rank | Option | For | Against |
|------|--------|-----|---------|
| 1 | Hold it for a person: it stays out of the bank on a review list, next to the question it resembles and the reason, and a replacement is generated meanwhile | No possible copy enters the bank and no possibly good question is lost. Only that one question waits; generation carries on. | Needs a person eventually. |
| 2 | Let it in with a warning flag | Nothing is lost and nothing waits. | A copy may already be in the bank, and in later prompts, before anyone looks. |
| 3 | Reject it like a duplicate | The bank stays clean with no human step. | Good questions are thrown away. |

**Chosen:** option 1, hold for a person.

**Why:** it is the only option that makes neither mistake automatically. It also matches the assignment's wording for Q8, "review context".

## D10. Which local embedding model (Question 2)

**Date:** 2026-10-12

**Question:** D6 chose a local model for the search stage. Which one?

**Evidence:** each model searched the ten assignment questions for each of the 50 questions in our answer key (`q2-duplicate-questions/experiments/choose_embedding_model.py`; results in `experiments/results/embedding_model_choice.json`). Of the 50, 34 have a partner among the ten. The search stage hands the nearest questions to the judge, so what matters most is whether the partner is among them. CPU time is per question on this laptop without using the graphics card.

| Option | Size | Partner nearest | Partner in nearest three | CPU time per question |
|--------|------|-----------------|--------------------------|-----------------------|
| TF-IDF on words (reference) | none | 29 of 34 | 32 of 34 | instant |
| all-MiniLM-L6-v2 | 23 M parameters, 87 MB | 30 of 34 | 33 of 34 | 8 ms |
| all-mpnet-base-v2 | 110 M parameters, 418 MB | 31 of 34 | 33 of 34 | 57 ms |
| Qwen3-Embedding-0.6B | 596 M parameters, 1.1 GB | 32 of 34 | 34 of 34 | 1.1 s |
| Qwen3-Embedding-0.6B with the task instruction | same | 30 of 34 | 34 of 34 | 2.5 s |
| gemini-embedding-001 (online, reference) | none | 32 of 34 | 34 of 34 | not measured |

**Re-measured on 2026-10-15** after the data audit (9 redundant or biased questions removed, 6 added; the answer key now has 47 questions, 34 of them partnered):

| Option | Partner nearest | Partner in nearest three | CPU time per question |
|--------|-----------------|--------------------------|-----------------------|
| TF-IDF on words | 27 of 34 | 32 of 34 | instant |
| all-MiniLM-L6-v2 | 27 of 34 | 33 of 34 | 10 ms |
| all-mpnet-base-v2 | 30 of 34 | 33 of 34 | 49 ms |
| Qwen3-Embedding-0.6B | 32 of 34 | 34 of 34 | 1.0 s |
| Qwen3-Embedding-0.6B with the task instruction | 29 of 34 | 34 of 34 | 2.2 s |
| gemini-embedding-001 | 32 of 34 | 34 of 34 | not measured |

The ranking, and therefore the choice below, did not change.

Two further findings:

- No model's score can decide "duplicate or not" by itself. With Qwen3, the different question C35 ("The angle of reflection is 30°. What is the angle between the incident ray and the reflected ray?") scores 0.95, above most true duplicates, while the fill-in-the-blank duplicate C26 scores 0.78. This confirms D3 and D4: the score finds candidates, the judge decides.
- The task instruction, which widened the gap from +0.01 to +0.11 on the ten assignment questions, gave no gain on the 50 harder ones and doubled the time.

| Rank | Option | For | Against |
|------|--------|-----|---------|
| 1 | Qwen3-Embedding-0.6B, without the instruction | Found every partner. The search is the one step the judge cannot correct: a partner never shown is never judged. A 2025 model, 26 times larger than MiniLM; its [model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) reports 86.6 on the MTEB English v2 sentence-similarity tasks. | A 1.1 GB download once. About 1 second per question on a machine without a graphics card (0.03 s with one). |
| 2 | all-MiniLM-L6-v2 | Tiny and instant on any machine. One partner behind here. | A smaller 2021 model; the one partner it missed may become many in a large bank. No score for it on the same benchmark version was found, so the two cannot be compared there directly. |
| 3 | Qwen3-Embedding-0.6B with the instruction | Same partners found as option 1. | Twice as slow, fewer partners ranked first. |
| 4 | all-mpnet-base-v2 | Middle size. | No better than MiniLM here, but five times bigger and slower. |

**Chosen:** option 1, Qwen3-Embedding-0.6B without the instruction.

**Why:** finding the partner is the step where a miss cannot be repaired later, so quality there is worth the size. The reviewer's machine is protected by saving the demo's results in the repository, so the demo does not need the model downloaded.

**Limits:** 34 partnered questions is a small sample, and the corpus has only six distinct questions, so "nearest three" is an easy target. The measurement must be repeated on a bank of hundreds. Six further small models could not be tested because their downloads did not finish.

## D11. Which LLM judges, and how (Question 2)

**Date:** 2026-10-15

**Question:** which LLM makes the final call, and should one model decide alone?

**Evidence:** five models judged the same 40 non-copy questions from the answer key (`experiments/choose_judge_model.py`), and combinations of them were replayed from the saved answers (`experiments/combine_judges.py`). "Harmful" means a copy let into the bank or a new question blocked.

| Option | Correct of 40 | Harmful mistakes | Unclear cases decided without a person | Sent to a person | AI answers used |
|--------|---------------|------------------|-----------------------------------------|------------------|-----------------|
| `gpt-oss-120b` + `qwen3.8-27b`, referee `gemini-3.8-flash` on disagreement | 37 | 0 | 2 | 1 | 84 |
| `gpt-oss-120b` + `qwen3.8-27b`, disagreement to a person | 35 | 0 | 2 | 3 | 80 |
| Majority vote of `gpt-oss-120b`, `qwen3.8-27b`, `gpt-oss-20b` | 36 | 1 | 3 | 0 | 120 |
| `gpt-oss-120b` alone | 35 | 1 | 3 | 0 | 40 |
| `gemini-3.5-flash-lite` alone | 32 | 0 | 1 | 2 | 40 |
| `gemini-3.5-flash-lite` first, `gpt-oss-120b` when it is unsure | 33 | 1 | 3 | 0 | 44 |
| `gemini-3.8-flash` alone | 32 answered, all right | 0 | 0 | 0 | stopped after its free allowance of 20 a day |

Two findings shaped the choice. A single model rarely says "not sure": `gpt-oss-120b` decided all three unclear cases itself. And a model's own confidence is no guide: `gemini-3.5-flash-lite` rated itself 4 or 5 out of 5 on every answer it got wrong.

**Chosen:** two judges, `gpt-oss-120b` and `qwen3.8-27b` (both on Groq), and only when they disagree a referee, `gemini-3.8-flash`. The referee's answer counts when it matches one of the two judges; otherwise, or when the referee cannot be reached, the question is held for a person (D9).

**Why:** it was the best setup on every measure that matters: most correct, no harmful mistakes, and the fewest questions left for a person. Disagreement between two different models is used as the signal that a question is unclear, which a single model does not give. The referee is needed for about one question in ten, which fits inside its free allowance.

**Limits:** all setups were compared on the same 40 questions used to pick them, so the winner's score is optimistic; the assignment's own Q1–Q10 check is the independent test. Both judges are on Groq, so if Groq is unreachable (as happened through one VPN server) new questions are held for a person.

**Re-measured on 2026-10-15** after the data audit, on the 41 non-copy questions of the audited answer key, with the panel run for real (not replayed): 38 of 41 correct, no copy let in, no new question blocked, 2 unclear cases decided without a person, 1 question sent to a person. By kind: semantic duplicates 16 of 16, variants 6 of 6, different 12 of 13, needs review 4 of 6. On the 6 questions written after the first tests it got 6 of 6. `gpt-oss-120b` alone got 36 of 41, `qwen3.8-27b` alone 36, `gemini-3.5-flash-lite` 33, `gpt-oss-20b` 33.

**Addition on 2026-10-15 (made by Claude):** a backup referee, `gemini-3.5-flash-lite`, is asked when `gemini-3.8-flash` cannot answer. The first demo run used up the referee's 20 daily requests, after which every disagreement went to a person. As a referee, `gemini-3.5-flash-lite` made no harmful mistakes in the replayed comparison (36 of 41 correct).

## D12. Which LLM writes new questions and which labels concepts (Question 2)

**Date:** 2026-10-15

**Made by:** Claude, without asking, because the user asked to finish quickly; recorded here so the user can change it.

| Rank | Option | For | Against |
|------|--------|-----|---------|
| 1 | `gemini-3.5-flash-lite` for both, writer at temperature 0.7, labeler at 0 | A different model family from the two judges, so the judges are not marking their own writing (models tend to rate their own output kindly). Fast, and its free allowance was never reached in testing. | Less capable than the larger models, so its questions may be plainer. |
| 2 | `gpt-oss-120b` as writer | Stronger writer. | It is also the first judge, so it would judge its own questions; it shares Groq's per-minute limit with the judging. |
| 3 | `gemini-3.8-flash` as writer | Strongest Gemini model tested. | 20 requests a day, which the referee needs. |

**Chosen:** option 1 for writing.

**Revised on 2026-10-15 for labelling (made by Claude):** the first demo run showed `gemini-3.5-flash-lite` labelling badly: all ten assignment questions got "laws of reflection", and after a stricter prompt it still gave Q1 and Q3 (the same question) different labels. `gpt-oss-20b`, which has no other job, labelled the ten consistently: the six definition questions shared one label, the laws and angle questions another, and regular-versus-diffuse its own, and generated questions on lateral inversion and multiple reflection got those labels. Its own syllabus was narrower (mostly curved mirrors).

**Revised again on 2026-10-15 for the syllabus (made by Claude):** with `gemini-3.5-flash-lite` listing the syllabus, its list began with general light topics (nature of light, luminous objects, rectilinear propagation), even after it was told to stay inside the subject. The gap-targeting then steered the writer to those topics, and the second demo run produced off-subject questions, two of them on quantum theory. `gpt-oss-120b` listed 19 points that all belong to reflection, from the law and the angles through specular and diffuse reflection, lateral inversion and multiple reflections to curved mirrors. It is asked once per subject, so its use as a judge is not affected. Final: writer `gemini-3.5-flash-lite`, syllabus `gpt-oss-120b`, labeler `gpt-oss-20b`.

## D13. How the coverage summary is built (Question 2)

**Date:** 2026-10-15

**Made by:** Claude, without asking, because the user asked to finish quickly; recorded here so the user can change it.

| Rank | Option | For | Against |
|------|--------|-----|---------|
| 1 | Concept labels: an LLM lists the subject's syllabus points once, labels each question with one of them (reusing existing labels), and the summary counts questions per label; the gaps are syllabus points with the fewest questions | The same labels feed the detector's second search route (D4), so one mechanism serves both. Readable by the writer and by a person. Can name gaps that have no questions yet. | One LLM call per new question. Labels depend on the labeler and can drift; reusing the known list keeps them compact, as in [Ma 2026](https://aclanthology.org/2026.aimecon-sessions.9.pdf) Method 2. |
| 2 | Grouping embeddings into clusters | No LLM call per question. | Clusters have no names for the writer to read, and an empty topic has no cluster, so gaps cannot be named. |
| 3 | Both | Most information. | Two mechanisms to build and explain for little gain. |

**Chosen:** option 1.

## D14. How questions are stored (Question 2)

**Date:** 2026-10-15

**Made by:** Claude, without asking, for the same reason.

| Rank | Option | For | Against |
|------|--------|-----|---------|
| 1 | One readable JSON file per bank; vectors recomputed when it is loaded | Nothing to install; the file can be read and checked by hand; fits a bank of thousands. | Recomputing vectors takes seconds per thousand questions on a graphics card; a bank of hundreds of thousands would want stored vectors and a database. |
| 2 | SQLite with stored vectors | Scales further; safe with several users. | More code and a binary file a reviewer cannot read. |
| 3 | A vector database server | Built for millions of vectors. | Far beyond the assignment's size; another service to run. |

**Chosen:** option 1, with the upgrade path (stored vectors, then an approximate index such as FAISS) described in the README.

## Pending

None for Question 2.
