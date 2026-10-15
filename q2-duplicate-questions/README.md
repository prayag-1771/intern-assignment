# Question 2: generating questions without duplicates

Solution for [Question 2](../questions/question-2-duplicate-questions.md): an LLM generates new questions for an existing bank, a generation loop steers it away from what the bank already covers, and an independent detector checks every new question and catches what prevention misses.

Every design choice below was measured before it was made. The options considered and the evidence for each choice are in [decision.md](../decision.md) (D3 to D14); the step-by-step history is in [log.md](../log.md).

## Results at a glance

| What was checked | Result |
|---|---|
| The assignment's ten questions, classified in order (each against the ones before it) | see [examples/REPORT.md](examples/REPORT.md) §1 |
| Exact duplicates in our 47-question answer key, caught by text alone | 6 of 6, and no false matches among the other 41 |
| Search: the right existing question among those shown to the judges | 28 of 28 non-copy questions that have one |
| Judges on the 41 non-copy questions of the answer key | 38 correct; no copy let in, no new question blocked; 2 unclear cases decided, 1 sent to a person |
| Same, by kind of question | semantic duplicates 16/16, variants 6/6, different 12/13, needs review 4/6 |
| Generation: memory-guided loop against a writer that never sees the bank | see [examples/REPORT.md](examples/REPORT.md) §2 |

The answer key is small and was written by us, so these numbers show the method works on hard cases; they are not a precise accuracy estimate. See [Evaluation](#evaluation) for how it would be measured properly.

## How it works

```
                 ┌──────────── generation loop (prevention) ────────────┐
 subject ──►     │ prompt rebuilt each round from the bank:              │
 bank    ──►     │  coverage summary · gaps · nearest existing questions │──► writer LLM ──► new questions
                 │  · last round's rejections and why                    │                       │
                 └───────────────────────────────▲──────────────────────┘                       │
                                                 │ rejected (with reason)                        ▼
                 ┌──────────── independent detector (safety net) ───────────────────────────────┐
                 │ 1. exact check: cleaned-text fingerprint lookup                               │
                 │ 2. search: 5 nearest by meaning (local embeddings) + up to 3 sharing the      │
                 │    question's concept label                                                   │
                 │ 3. judges: two LLMs label the question against those few, together;          │
                 │    a referee LLM is asked only if they disagree                               │
                 └───────────────┬───────────────────────────┬──────────────────┬───────────────┘
                                 ▼                           ▼                  ▼
                       different: joins the bank     duplicate / variant:   needs review:
                                                     rejected               held for a person
```

### What counts as a duplicate

One written rule, the **perfect-answer test**: two questions are the same if a perfect answer to one would earn full marks on the other. The judges apply it by comparing the *concept* (what the question is about) and the *task* (define, state, calculate, compare, ...). This is the only rule we found that reproduces the assignment's labels: Q6 ("What is the angle of reflection?") and Q7 (a calculation of it) share a concept but not a task, so they are different.

The detector gives one of five labels:

| Label | Meaning | Example |
|---|---|---|
| exact duplicate | same text once case, spacing, punctuation, numbering and bold marks are ignored | Q10 and Q2 |
| semantic duplicate | same concept and task in other words or another format (multiple choice, fill in the blank); also existing questions joined into one | Q2 and Q1 |
| variant | same concept, task and method; only the numbers change | Q7 with 45° instead of 30° |
| different | another concept, or the same concept with another task | Q6 and Q7 |
| needs review | broader, narrower or vaguer than an existing question, so it depends on context | Q8 "What is reflection?" against Q1 |

Variants are rejected by default, since a generator could otherwise fill the bank by changing numbers. "Needs review" questions are held out of the bank until a person decides; a replacement is generated meanwhile.

### Independent detection ([qbank/detector.py](qbank/detector.py))

1. **Exact check** ([qbank/text.py](qbank/text.py)). The text is cleaned (case, spacing, sentence punctuation, a leading "1)" or "Q3.", markdown bold) and hashed; a copy is found with one dictionary lookup. Cleaning is deliberately cautious: digits, decimal points, quotes and maths symbols are kept, so "5 + 3" never matches "5 − 3" and "5!" never matches "5". A copy it misses is still caught by the later steps; a wrong match here would be final.
2. **Search** ([qbank/search.py](qbank/search.py)). Two routes find the few stored questions worth showing to the judges:
   - *by meaning*: the 5 nearest by cosine similarity of [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) vectors, run locally;
   - *by concept*: up to 3 more that share the new question's concept label, which catches a duplicate worded too differently for the embedding to rank it near.
   Similarity scores are only used to find candidates, never to decide: in our tests a different question scored 0.95 while a true duplicate scored 0.78.
3. **Judges** ([qbank/judge.py](qbank/judge.py)). `gpt-oss-120b` and `qwen3.8-27b` (on Groq) each label the new question against the shown questions *together*, so a question that joins two existing ones can be recognised. They work from the written rule and six worked examples on another topic (Ohm's law), so nothing from the test data is in the prompt. If they agree, that is the answer; if not, `gemini-3.8-flash` is asked as referee and counts only if it backs one of them; otherwise the question is held for a person. Disagreement between two different models is our signal that a question is unclear: single models almost never say "not sure". Any unusable reply also holds the question rather than letting it through.

The detector reads only the question text and the bank. It ignores everything the generator says about its own questions, including the concept it claims, so it still works when prevention fails or when questions come from elsewhere.

### Generation-time avoidance ([qbank/generator.py](qbank/generator.py))

Each round, the writer's prompt is rebuilt from the bank:

- **Coverage summary**: concept labels and how many questions each has (the 20 largest).
- **Gaps**: the 5 syllabus points with the fewest questions, to aim at. The syllabus is listed once by an LLM for the subject.
- **Already asked**: up to 12 stored questions nearest to those gaps and to the subject, marked "do not repeat, reword, renumber or reformat".
- **Feedback**: last round's rejected questions and what they repeated.

The writer is told what does and does not count as new (the same rule the judges use). Every new question then goes through the independent detector; only "different" ones join the bank. Rounds continue until enough are accepted.

**Context limits and scale.** Every part of the prompt has a fixed maximum, so the prompt is the same size for a bank of 10 or 100,000 questions; the bank is searched, never pasted in. This follows [Lingo and Chhajer 2026](https://arxiv.org/abs/2604.07147), who found that deduplication alone and prompt evolution alone are "individually insufficient but jointly effective".

### Tags and metadata ([qbank/bank.py](qbank/bank.py))

Questions carry free key-value tags (`subject=physics`, `grade=8`, `source=generated`, ...); new keys and values can be added at any time and are used to organise and filter (`python -m qbank list source=generated`). **The duplicate checks never read them**: a test confirms that a copy with different tags is still caught. The concept labels used by the search and the coverage summary are a different thing: they are read from the question text by an LLM, so detection stays content-based.

## Technology choices and trade-offs

| Part | Choice | Main alternatives and why not |
|---|---|---|
| Embeddings | Qwen3-Embedding-0.6B, local (D6, D10) | Gemini embeddings: a key and a request per question, 40 times slower, can be withdrawn. MiniLM: instant but missed a partner the judge then never sees. TF-IDF: ranks duplicates *below* different questions (Q3/Q4 score 0.12, Q6/Q7 0.80). |
| Decision | LLM judges on the few nearest questions (D3, D4) | Cut-offs on similarity: no cut-off separates our classes. LLM against every stored question: thousands of calls per new question. |
| Judges | two models + referee (D11) | One model: 36 of 41 and never says "not sure". Majority of three: hides doubt. Cheap model first: its confidence was 4–5 out of 5 even when wrong. |
| Writer and labeler | `gemini-3.5-flash-lite` (D12) | Using a judge model as writer would have it mark its own work. |
| Storage | one readable JSON file, vectors recomputed on load (D14) | SQLite or a vector database: more to run, needed only at much larger sizes. |

Costs per new question: one labeler call and two judge calls (a third only on disagreement, about one in ten). The cost does not grow with the bank: the search is one matrix product, exact up to tens of thousands of questions; beyond that an approximate index (FAISS) replaces it with no other change.

## Evaluation

**Data.** The assignment's ten questions contain no hard cases, so we wrote an answer key of 47 more ([data/labelled_candidates.json](data/labelled_candidates.json)), each labelled with the perfect-answer test *before* any judge saw it: copies with formatting changes, rewordings including very different wordings and other formats, number swaps, look-alikes that test something else ("refraction" for "reflection"), and unclear cases. An audit removed 9 questions that were redundant, off the subject, or worded like the judge's own examples (removing them could only lower the scores), and added 6 for the thinnest cases; results on those 6 are reported separately because they were written after the first tests.

**Measures.** Results are reported per kind of question and per kind of error, not as one accuracy: the key's mix of kinds is not the real-world mix, and the errors differ in cost. Letting a copy in or blocking a new question is harmful; sending a clear case to a person only costs time. The search stage is measured on its own (is the right question shown to the judges at all?), because the judges cannot fix a miss there.

**What we would do with more time.**
- A larger, independently labelled set: questions from several subjects, each labelled by two or more teachers, with their agreement measured. Experts themselves disagree on unclear cases (four reviewers ranged from 0.70 to 0.91 recall in [Ma 2026](https://aclanthology.org/2026.aimecon-sessions.9.pdf)), which caps any measured accuracy.
- A held-out split: tune prompts on one part, report on the other. Our judge setup was chosen on the same questions it was scored on, so its score is optimistic.
- Search recall on a bank of thousands, where "among the nearest five" is a hard target; ours had six distinct questions.
- Performance: requests and seconds per new question, and the share needing a person, on a realistic stream of mostly new questions.

## Limits

- 47 test questions on one topic, written by one person: enough to show behaviour on hard cases, not to estimate accuracy precisely.
- Both judges are on Groq. Through one VPN server Groq refused all requests; questions are then held for a person, which is safe but stops automatic acceptance.
- `gemini-3.8-flash`, the referee, allows 20 requests a day on the free plan; beyond that, disagreements go to a person.
- The concept route added nothing measurable on this small bank (the embedding search already showed every partner); its value is expected on larger banks with very different wordings.

## Running it

```bash
cd q2-duplicate-questions
pip install -r requirements.txt          # Python 3.11
python -m pytest                         # 86 tests; no keys or downloads needed
python -m examples.run_demo              # rebuilds examples/REPORT.md from cached AI replies
python -m qbank check "Define the reflection of light."
python -m qbank generate 5               # needs GROQ_API_KEY and GEMINI_API_KEY in ../.env
python -m qbank review                   # questions held for a person
python -m qbank resolve N12 new          # or: duplicate
```

Every AI reply is cached in `data/llm_cache/`, keyed by the exact request, so the experiments and the demo repeat exactly without keys. New questions need the keys in `.env` (see `.env.example`). The embedding model (1.1 GB) downloads on first use; it runs on a GPU if present and on the CPU otherwise (about one second per question).

## Layout

| Path | What it is |
|---|---|
| `qbank/` | the package: text clean-up, embeddings, search, judges, concept labels, detector, bank, generator, command line |
| `data/corpus.json` | the assignment's ten questions and their expected labels |
| `data/labelled_candidates.json` | our 47-question answer key, with the audit record |
| `data/llm_cache/` | every AI reply used, so results repeat without keys |
| `experiments/` | the measurements behind each decision, with results in `experiments/results/` |
| `examples/` | the end-to-end demo and its report |
| `tests/` | unit tests, using stand-ins for every model |
