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

### Question 2: research into available approaches

- Searched research papers, patents, competition results and deployed systems for ways to (a) detect duplicate questions and (b) stop an LLM from generating them. The 36 sources relied on are listed below. No code was written.
- Finding 1: every field with this problem (exam item banks, record matching, LLM answer caches, retrieval competitions) uses the same shape: a cheap wide search, then a careful judge on the few survivors. This supports decision D3.
- Finding 2: the search stage can miss real duplicates before the judge sees them. A deployed exam system found 96.2% of known duplicate pairs on one exam and 47.3% on another with the same pipeline (Ma 2026). The search stage has to be measured separately, and a second way of finding candidates (concept tags) is the known fix.
- Finding 3: one fixed similarity cut-off gives unpredictable error rates (vCache). Published pipelines use anything from 0.85 to 0.99. Cut-offs must be calibrated on labelled pairs, with a review band kept.
- Finding 4: for the LLM judge, the written definition and examples matter more than the model. In Ma 2026 a model change cut recall from 0.75 to 0.54 and a prompt rewrite raised it to 0.82. Four human experts on the same pairs ranged from 0.70 to 0.91 recall, so "needs review" is a legitimate third answer.
- Finding 5: when generating, filtering afterwards is not enough alone. Lingo and Chhajer 2026 report that deduplication and rebuilding the prompt from memory are "individually insufficient but jointly effective"; on exam questions their repeat rate fell from 34.0% to 0.0%.
- Not obtained: the first-place write-up of Kaggle's Quora Question Pairs competition would not load, so it is not relied on.
- Depth of reading: the full text was consulted for Ma 2026, Lingo and Chhajer 2026, Islam et al. 2026, Manem et al. 2025, Wang et al. 2023 (Self-Instruct), Kuhn et al. 2023 and Guo et al. (League of LLMs). The other papers were checked at abstract level, the patents on their Google Patents pages, and Becker and Kao 2022 only as cited in Ma 2026. Anything quoted in the final write-up from an abstract-level source should be re-checked against the full paper first.
- Commit: `Log Question 2 research and sources`.

#### Sources: duplicate detection in exam and question banks

- Ye Ma. "From Validation to Resilience: Sustaining Measurement Quality in AI-Assisted Enemy Item Identification." Proceedings of the Artificial Intelligence in Measurement and Education Conference (AIME-Con), Volume 3: Coordinated Session Papers, pages 76–81, 2026. https://aclanthology.org/2026.aimecon-sessions.9.pdf
- Kirk A. Becker and Shu-Chuan Kao. "Identifying enemy item pairs using natural language processing." Journal of Applied Testing Technology, 23:41–52, 2022. (not read; known only as cited and described in Ma 2026)
- Jing Huang, Jihong Zhang, Hua-Hua Chang. "A Dual-Dimensional LLM Framework for Automated Item Incidental Content Similarity Analysis in Large-Scale Assessments." arXiv:2608.24825, 2026. https://arxiv.org/abs/2608.24825
- Yubo Shu, Hansu Gu, Peng Zhang, Tun Lu, Ning Gu. "An Intent-based and Annotation-free Method for Duplicate Question Detection in CQA Forums." Findings of the Association for Computational Linguistics: EMNLP 2023, pages 8889–8899. https://aclanthology.org/2023.findings-emnlp.596/
- Maksimjeet Chowdhary, Sanyam Goyal, Venktesh V, Mukesh Mohania, Vikram Goyal. "Unsupervised Question Duplicate and Related Questions Detection in e-learning platforms." WSDM 2023 demo paper; arXiv:2301.05150. https://arxiv.org/abs/2301.05150

#### Sources: patents

- US 10,741,093 B2. "Automated determination of degree of item similarity in the generation of digitized examinations." ACT; inventor Richard Meisner; granted 2020-08-11. https://patents.google.com/patent/US10741093B2/en
- US 12,548,459 B1. "System and method for preparing practice tests using machine learning models." Quizlet Inc; inventors Tingting Lin and Derrick Bonafilia; granted 2026-02-10. https://patents.google.com/patent/US12548459B1/en
- US 12,277,870 B2 (published as US 2022/0415203 A1). "Interface to natural language generator for generation of knowledge assessment items." Prometric LLC; granted 2025-04-15. https://patents.google.com/patent/US20220415203A1/en

#### Sources: detection methods in general

- Sentence Transformers documentation, "Retrieve & Re-Rank." https://sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html
- Sentence Transformers documentation, "Paraphrase Mining." https://sbert.net/examples/sentence_transformer/applications/paraphrase-mining/README.html
- Model card, `cross-encoder/quora-roberta-large` (trained on the Quora Duplicate Questions dataset). https://huggingface.co/cross-encoder/quora-roberta-large
- Model card, `microsoft/deberta-v2-xlarge` (results table: DeBERTa-V2-XXLarge reaches 92.7 accuracy / 90.3 F1 on the Quora Question Pairs development set). https://huggingface.co/microsoft/deberta-v2-xlarge
- Yuan Zhang, Jason Baldridge, Luheng He. "PAWS: Paraphrase Adversaries from Word Scrambling." NAACL 2019. https://aclanthology.org/N19-1131/
- Qihuang Zhong, Liang Ding, Juhua Liu, Bo Du, Dacheng Tao. "Can ChatGPT Understand Too? A Comparative Study on ChatGPT and Fine-tuned BERT." arXiv:2302.10198, 2023. https://arxiv.org/abs/2302.10198
- Ralph Peeters, Aaron Steiner, Christian Bizer. "Entity Matching using Large Language Models." Proceedings of the 28th International Conference on Extending Database Technology (EDBT), 2025; arXiv:2310.11244. https://arxiv.org/abs/2310.11244
- Tianshu Wang, Xiaoyang Chen, Hongyu Lin, Xuanang Chen, Xianpei Han, Hao Wang, Zhenyu Zeng, Le Sun. "Match, Compare, or Select? An Investigation of Large Language Models for Entity Matching." COLING 2025; arXiv:2405.16884. https://arxiv.org/abs/2405.16884
- Lingjiao Chen, Matei Zaharia, James Zou. "FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance." arXiv:2305.05176, 2023. https://arxiv.org/abs/2305.05176
- Luis Gaspar Schroeder, Aditya Desai, Alejandro Cuadron, Kyle Chu, Shu Liu, Mark Zhao, Stephan Krusche, Alfons Kemper, Matei Zaharia, Joseph E. Gonzalez. "vCache: Verified Semantic Prompt Caching." ICLR 2026; arXiv:2502.03771. https://arxiv.org/abs/2502.03771
- Asmit Kumar Singh, Haozhe Wang, Laxmi Naga Santosh Attaluri, Tak Chiam, Weihua Zhu. "Asynchronous Verified Semantic Caching for Tiered LLM Architectures." arXiv:2602.13165, 2026. https://arxiv.org/abs/2602.13165
- Lorenz Kuhn, Yarin Gal, Sebastian Farquhar. "Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Natural Language Generation." ICLR 2023; arXiv:2302.09664. https://arxiv.org/abs/2302.09664
- Amro Abbas, Kushal Tirumala, Dániel Simig, Surya Ganguli, Ari S. Morcos. "SemDeDup: Data-efficient learning at web-scale through semantic deduplication." arXiv:2303.09540, 2023. https://arxiv.org/abs/2303.09540
- SemHash, an open-source semantic deduplication library by MinishLab. https://minish.ai/packages/semhash
- FAISS wiki, "Guidelines to choose an index." https://github.com/facebookresearch/faiss/wiki/Guidelines-to-choose-an-index
- Eedi, "From Wrong Answers to Real Insights: How We Used a Kaggle Challenge to Map Student Misconceptions" (the host's summary of the winning solutions of the Kaggle competition "Eedi - Mining Misconceptions in Mathematics"). https://www.eedi.com/news/from-wrong-answers-to-real-insights-how-we-used-a-kaggle-challenge-to-map-student-misconceptions

#### Sources: avoiding duplicates during generation

- Ryan Lingo, Rajeev Chhajer. "Dynamic Context Evolution for Scalable Synthetic Data Generation." arXiv:2604.07147, 2026. https://arxiv.org/abs/2604.07147
- Mohammed Saidul Islam, Negin Baghbanzadeh, Farnaz Kohankhaki, Afshin Cheraghi, Ali Kore, Shayaan Mehdi, Elham Dolatabadi, Arash Afkanpour. "Fine-Grained Benchmark Generation for Comprehensive Evaluation of Foundation Models." arXiv:2605.18824, 2026. https://arxiv.org/abs/2605.18824
- Chaitanya Manem, Pratik Prabhanjan Brahma, Prakamya Mishra, Zicheng Liu, Emad Barsoum. "SAND-Math: Using LLMs to Generate Novel, Difficult and Useful Mathematics Questions and Answers." MATH-AI workshop at NeurIPS 2025; arXiv:2507.20527. https://arxiv.org/abs/2507.20527
- Yizhong Wang, Yeganeh Kordi, Swaroop Mishra, Alisa Liu, Noah A. Smith, Daniel Khashabi, Hannaneh Hajishirzi. "Self-Instruct: Aligning Language Models with Self-Generated Instructions." ACL 2023; arXiv:2212.10560. https://arxiv.org/abs/2212.10560
- Qianhong Guo, Wei Xie, Xiaofang Cai, Enze Wang, Shuoyoucheng Ma, Xiaobing Sun, Tian Xia, Kai Chen, Xiaofeng Wang, Baosheng Wang. "League of LLMs: A Benchmark-Free Paradigm for Mutual Evaluation of Large Language Models." arXiv:2507.22359. https://arxiv.org/abs/2507.22359
- Jiayi Zhang, Simon Yu, Derek Chong, Anthony Sicilia, Michael R. Tomz, Christopher D. Manning, Weiyan Shi. "Verbalized Sampling: How to Mitigate Mode Collapse and Unlock LLM Diversity." arXiv:2510.01171. https://arxiv.org/abs/2510.01171
- Yue Yu, Yuchen Zhuang, Jieyu Zhang, Yu Meng, Alexander Ratner, Ranjay Krishna, Jiaming Shen, Chao Zhang. "Large Language Model as Attributed Training Data Generator: A Tale of Diversity and Bias." NeurIPS 2023 Datasets and Benchmarks Track; arXiv:2306.15895. https://arxiv.org/abs/2306.15895
- Steven Moore, Robin Schmucker, Tom Mitchell, John Stamper. "Automated Generation and Tagging of Knowledge Components from Multiple-Choice Questions." Learning @ Scale 2024; arXiv:2405.20526. https://arxiv.org/abs/2405.20526

#### Sources: models and services we could use

- Model card, `Qwen/Qwen3-Embedding-0.6B` (includes a benchmark table comparing embedding models). https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
- Model card, `google/embeddinggemma-300m`. https://huggingface.co/google/embeddinggemma-300m
- Gemini API documentation, "Embeddings." https://ai.google.dev/gemini-api/docs/embeddings
- Groq documentation, "Models." https://console.groq.com/docs/models

### Question 2: approach decided

- **Decision (D4):** the detector is layered with one search route: exact-text match, then an embedding search for the nearest few stored questions, then an LLM that compares the new question with those few together against a written definition of "duplicate". A second search route based on concept tags is added only if measurement shows the search stage missing duplicates. Chosen over six alternatives; see `decision.md`.
- **Decision (D5):** generation uses a memory-guided loop: each round the prompt is rebuilt from the bank (a coverage summary, the nearest existing questions, the thinnest topics), new questions are screened, and rejects are fed back. Chosen over five alternatives; see `decision.md`.
- D4 also sets five build rules: measure the search stage on its own, calibrate cut-offs on labelled pairs, give the judge a written definition, fix the judge model, and report found-and-correct counts instead of one accuracy number.
- Commit: `Record detection and generation decisions`.

### Question 2: detection decision revised

- **Decision (D4, revised):** the detector uses two search routes from the start: the embedding search plus a concept-tag search, then the LLM judge. It is built in two steps, the one-route detector first and the tag route second, and results are reported with and without the tag route.
- Reason for the change: the earlier plan (add tags only if measurements showed misses) relied on the test set containing hard cases, and the ten given questions contain none. The prompt also names "effectively equivalent" questions, and the tags can be shared with the generation side.
- Two build rules were added to D4: the labelled test set must include hard pairs, and the search stage is reported with and without the tag route.
- Commit: `Revise detection decision to two search routes`.

### Question 2: build started

- Go-ahead given to start building, with every decision still put to the user first.
- Created one folder per question: `q2-duplicate-questions/` for this work and `q1-image-catalog/` (a README only for now) for Question 1.
- Created a Python environment in `.venv/` at the repository root (not tracked). It reuses the GPU build of PyTorch already on this machine and adds `sentence-transformers`. Downloaded models are kept in `.cache/` (not tracked).
- Language is Python for both questions: the embedding and LLM libraries this work needs are Python-first.
- Added `q2-duplicate-questions/data/corpus.json`: the ten assignment questions with their expected labels, restated in a form code can read. For Q8 the assignment names no partner question; reading it as ambiguous against Q1 is ours.
- Added the package `q2-duplicate-questions/qbank/` with `config.py` (paths and optional API keys) and `embedders.py` (one interface for turning questions into vectors, with a local-model version and a Gemini version).
- Added `q2-duplicate-questions/requirements.txt` and a short README.

### Question 2: embedding comparison

- Added `q2-duplicate-questions/experiments/compare_embeddings.py`. It scores every pair of the ten questions with each option and reports the lowest-scoring duplicate pair, the highest-scoring different pair, and the gap between them. Results are saved in `experiments/results/embedding_comparison.json`.
- Options scored: TF-IDF on words and on character n-grams (the conventional baseline), three local models (`all-MiniLM-L6-v2`, `all-mpnet-base-v2`, `Qwen3-Embedding-0.6B` with and without a one-line task instruction), and Gemini's `gemini-embedding-001`.
- Result, TF-IDF: it ranks the pairs backwards. The duplicates Q3/Q4 score 0.12 and the different pair Q6/Q7 scores 0.80, a gap of -0.67.
- Result, transformer models: all put every duplicate pair above every different pair, but mostly by a narrow gap: +0.03 for MiniLM, +0.01 for mpnet, +0.01 for Qwen3 without the instruction, +0.03 for Gemini.
- Result, instruction: Qwen3 with the instruction "retrieve questions that are semantically equivalent" in front of each question gives a gap of +0.11, with duplicates at 0.94 or higher, Q8 at 0.86 to 0.89 and different pairs at 0.83 or lower.
- Result, speed for ten questions: local models take 0.2 to 0.4 seconds on the GTX 1650; Gemini takes 13.6 seconds (one request per question). On the CPU alone, MiniLM takes 0.09 seconds and Qwen3 takes 24.9 seconds.
- Limit: ten questions are too few to choose the exact model. The exact model is to be chosen on the larger labelled set that D4 requires.
- Added `tests/test_embedding_comparison.py` (3 tests, all passing) for the pair labels and the summary numbers, and `pytest.ini`.
- Commit: `Add Question 2 skeleton and embedding comparison`.
- Also sent one small test request to each candidate LLM (a throwaway script). All three Groq models and two Gemini models answered in valid JSON. Groq's free tier allows 1,000 requests a day and 8,000 tokens a minute per model; `gemini-2.5-flash` is no longer offered.

### Question 2: embedding source decided

- **Decision (D6):** a local model is the engine for embeddings; Gemini stays only in the comparison as a reference point. Chosen over a switchable local/Gemini pipeline, Gemini as the engine, and TF-IDF only. The measured table and the ranking are in `decision.md`.
- The exact local model is left open until the larger labelled set exists.
- Commit: `Record embedding source decision`.

### Question 2: rules for "same question" decided

- **Decision (D7):** two questions are the same if a perfect answer to one would earn full marks on the other, checked by comparing concept and task. Chosen over "same topic" (which contradicts the assignment's labels for Q6/Q7) and no written rule.
- **Decision (D8):** a question that only changes the numbers of an existing one gets its own label, "variant". It is not counted as new by default, and a setting can allow variants. Chosen over calling it a copy, sending it to review, or accepting it as new.
- **Decision (D9):** a "needs review" question is held out of the bank until a person decides, and a replacement is generated meanwhile. Chosen over letting it in with a warning and over rejecting it.
- The detector therefore has five labels: exact duplicate, semantic duplicate, variant, different, needs review.
- Commit: `Record duplicate rule, variant and review decisions`.

### Question 2: answer key drafted

- Added `q2-duplicate-questions/data/labelled_candidates.json`: 50 new questions, each labelled against the ten assignment questions using the D7 rule. This is the labelled test set that D4 requires, because the ten given questions contain no hard cases.
- Contents: 10 exact duplicates (case, spacing, punctuation, a question number, bold markers), 17 semantic duplicates (including three worded very differently, a multiple-choice form and a fill-in-the-blank form), 3 variants, 16 different questions (most of them look-alikes such as "refraction" for "reflection") and 4 needs-review questions.
- Six candidates are marked `judgement_call` because a careful person could label them otherwise. They are the ones put to the user for confirmation.
- Added `tests/test_data_files.py` (3 tests) so a typo in the data files cannot skew results.
- Limit: 50 questions on one topic, written by us. It is five times the given data and has the hard cases, but it is still small, so results will be reported as counts.
- Commit: `Add labelled answer key for Question 2`.

### Question 2: joined questions count as the same

- The user questioned one label in the answer key: "Define reflection of light and state its laws." had been marked "needs review". Their point: it is Q1 and Q5 joined, so answering it is answering both, and nothing new is asked.
- **Decision (added to D7):** a question made only by joining existing questions counts as the same as those questions. Candidate C48 is now a semantic duplicate of Q1 and Q5. A question that asks for only part of an existing one (C47) stays "needs review", because the two are not equal.
- Answer key counts are now 10 exact duplicates, 18 semantic duplicates, 3 variants, 16 different and 3 needs review. The data test was updated to match.
- Commit: `Treat joined questions as duplicates`.

### Question 2: answer key confirmed

- The user confirmed the remaining five judgement-call labels, so the answer key stands as committed.

### Question 2: embedding models tested on the answer key

- Added `qbank/datasets.py` (loads the corpus and the answer key, and works out which corpus questions are copies of each other) and moved the first experiment and its tests onto it.
- Added `experiments/choose_embedding_model.py` with `tests/test_embedding_model_choice.py`. For each of the 50 answer-key questions a model finds the nearest corpus questions. It reports whether the partner is nearest, whether it is among the nearest three (what the judge is shown), the lowest score of a question that has a partner, the highest score of a "different" question, and the time per question on the CPU. Results are in `experiments/results/embedding_model_choice.json`.
- Result, finding the partner among the nearest three (34 questions have a partner): TF-IDF 32, `all-MiniLM-L6-v2` 33, `all-mpnet-base-v2` 33, `Qwen3-Embedding-0.6B` 34 with or without the instruction, Gemini 34.
- Result, scores cannot decide alone: the "different" question C35 scores 0.95 with Qwen3 and 0.91 with MiniLM, above most true duplicates, while the fill-in-the-blank duplicate C26 scores 0.78 and 0.54. With the cut-off at the lowest partnered score, 11 to 14 of the 16 "different" questions still go to the judge. The score is therefore used only to find candidates and to skip clearly unrelated questions; the judge decides.
- Result, the instruction: on the ten assignment questions it widened the gap from +0.01 to +0.11, but on the 50 harder questions it gave no gain in finding the partner (34 either way), a lower nearest-right count (30 against 32) and twice the CPU time. The earlier result did not hold on more data.
- Result, CPU time per question: MiniLM 8 ms, mpnet 57 ms, Qwen3 1.1 s without the instruction and 2.5 s with it.
- Limits: 34 partnered questions is a small sample, so a difference of one question proves nothing. The corpus has only six distinct questions, so "among the nearest three" is an easy target; it must be measured again on a bank of hundreds.
- Not tested: six more small models (`paraphrase-MiniLM-L6-v2`, `bge-small-en-v1.5`, `quora-distilbert-base`, `paraphrase-mpnet-base-v2`, `bge-base-en-v1.5`, `gte-modernbert-base`). The connection to the model site dropped to about 0.26 MB a second and their downloads did not finish. The script keeps earlier results, so they can be added by running it again.
- Commit: `Add embedding model test on the answer key`.

### Question 2: building blocks written during the test run

- Added `qbank/text.py` with `tests/test_text.py`: the clean-up behind the exact-duplicate check. It ignores letter case, spacing, sentence punctuation, a leading question number and bold or italic marks, and keeps digits, decimal points and maths symbols, so "5 + 3" and "5 - 3", or "5!" and "5", never match. A test confirms that all ten exact duplicates in the answer key match their corpus partner and that no other candidate does. Commit: `Add text clean-up for exact duplicates`.
- Added `qbank/llm.py` with `tests/test_llm.py`: one small client for Groq and Gemini that returns JSON, retries when rate-limited, and saves every reply in a cache file so repeated requests need no key and no network. Commit: `Add LLM client with a reply cache`.
- Added `qbank/judge.py` with `tests/test_judge.py`: the judge's written instructions (the perfect-answer test, the four labels it may give, the joined-question and part-question cases, and six worked examples from another topic so that nothing from the answer key leaks into the prompt), and the handling of its replies. An unusable or missing reply holds the question for review, in line with D9. Commit: `Add the LLM judge`.
- These three are written and unit-tested (48 tests pass in total) but not yet run against a real LLM or wired together.

## 2026-10-12

### Question 2: embedding model decided

- **Decision (D10):** the search stage uses `Qwen3-Embedding-0.6B` without the task instruction. It was the only local model that put the partner among the nearest three for all 34 partnered questions. Chosen over `all-MiniLM-L6-v2`, the same Qwen3 model with the instruction, and `all-mpnet-base-v2`; see `decision.md`.
- Commit: `Record embedding model decision`.

### Question 2: detector assembled

- Added `qbank/search.py`: the bank's search stage. Exact copies are found with one lookup on the cleaned-text fingerprint. The nearest questions by meaning come from one matrix product over all stored vectors, which is exact and fast for tens of thousands of questions. Stored questions with the same wording as one already listed are skipped, so the judge's places are not wasted on Q2 and Q10 together.
- Added `qbank/detector.py`: the independent detector. Exact check first; otherwise the five nearest stored questions go to the judge together. It reads only the question text and the bank, nothing from generation.
- The judge is shown five questions. This is a setting (`SHOWN_TO_JUDGE`), not yet a decision put to the user; five is enough to cover a question joined from two others and still keeps the prompt short.
- `qbank/llm.py` now keeps one cache file per model in `data/llm_cache/`, so several models can run at the same time without overwriting each other's replies, and it counts replies and waiting time.
- Added `tests/test_detector.py` (8 tests, using a word-count stand-in for the embedding model and a stand-in judge) and `tests/test_judge_model_choice.py`. 66 tests pass.
- Commit: `Add search stage and detector`.

### Question 2: judge test started

- Added `experiments/choose_judge_model.py`. The search runs once with the chosen embedding model; then five candidate LLMs each judge the same 40 non-copy questions from the answer key: `gpt-oss-120b`, `gpt-oss-20b` and `qwen3.8-27b` on Groq, `gemini-3.8-flash` and `gemini-3.5-flash-lite` on Gemini. Each answer is sorted by its effect: correct, copy let in, new question blocked, unclear case decided without a person, wrong question named, sent to a person needlessly, wrong kind of block, or no answer.

### Question 2: judge test, first run

- Exact check: all 50 answer-key questions were handled correctly by text alone (the 10 copies matched, nothing else did).
- Search: for all 24 non-copy questions that have a partner, every expected partner was among the five questions shown to the judge.
- Groq refused every request with HTTP 403, "Access denied. Please check your network settings.", from all three models and even without a key. It worked on 2026-10-11. The machine's traffic was leaving through a data-centre network in Tokyo (Datacamp Limited), which looks like a VPN; Groq blocks many such networks. The user was asked to turn the VPN off so the Groq models can be tested.
- The run then crashed when one `gemini-3.8-flash` request timed out after 120 seconds: network errors were not caught. Fixed in `qbank/llm.py`: timeouts and dropped connections are now retried like rate limits, and if they persist the judge gets "unavailable", so that question is held for a person and the run carries on. A test was added (67 pass).
- The judge test now reports a model with no usable replies as "not scored" instead of counting 40 blank answers against it.
- Commit: `Retry network errors in the LLM client`.

### Question 2: judge test results

- Groq: still refused with HTTP 403 from this network, so its three models are "not scored".
- `gemini-3.8-flash`: answered 32 of the 40 questions and got all 32 right. The other 8 got no answer: its free plan allows 20 requests a day per model (the refusal names the quota `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, value 20). About 10 seconds per answer.
- `gemini-3.5-flash-lite`: answered all 40 and got 32 fully right. It made no serious mistake: no copy let in and no new question blocked. Its 8 slips: three same-number rewordings of Q7 called "variant" instead of "semantic duplicate" (blocked either way); two clear cases sent to a person (C17, and C36, a judgement call); one unclear case decided as a duplicate (C49); two unclear cases with a related but not the expected question named (C47, C50).
- On the 32 questions both answered, `gemini-3.8-flash` got 32 right and `gemini-3.5-flash-lite` 26.
- The "variant" slip suggests the judge's instructions should say plainly that a variant has different numbers and the same numbers in other words is a semantic duplicate. If the instructions are changed after seeing these results, the answer-key score becomes optimistic, so any change will be recorded and reported as such.
- Two fixes to `qbank/llm.py`: speed is now measured on successful replies only (the first run reported 1,530 seconds per reply because quota waits were counted), and a refusal saying the daily allowance is used up is no longer retried. A test was added (68 pass).
- The saved replies in `data/llm_cache/` are committed, so the test can be rerun without keys and without spending allowance.
- Commit: `Add judge test results and stop retrying used-up allowances`.

### Question 2: Groq judges tested

- The user changed the connection, and Groq accepted requests again (the traffic now left through a server in the Netherlands). The three Groq models were run on the same 40 questions; the Gemini replies came from the cache.
- Results, out of 40:

| Judge | Correct | Copy let in | New question blocked | Unclear case decided | Smaller slips | No answer | Seconds per answer |
|-------|---------|-------------|----------------------|----------------------|---------------|-----------|--------------------|
| `gpt-oss-120b` (Groq) | 35 | 0 | 1 (C36, a judgement call) | 3 | 1 | 0 | 4.3 |
| `gpt-oss-20b` (Groq) | 35 | 1 (C25, a judgement call) | 1 (C36) | 2 | 1 | 0 | 4.0 |
| `qwen3.8-27b` (Groq) | 35 | 1 (C17, a clear case) | 1 (C36) | 2 | 1 | 0 | 3.6 |
| `gemini-3.8-flash` | 32 | 0 | 0 | 0 | 0 | 8 (daily allowance) | about 10 |
| `gemini-3.5-flash-lite` | 32 | 0 | 0 | 1 | 7 | 0 | about 2 (from the 2026-10-11 probe) |

- On the 32 questions `gemini-3.8-flash` answered: it got 32 right, `gpt-oss-120b` and `qwen3.8-27b` 29, `gpt-oss-20b` 28, `gemini-3.5-flash-lite` 26. Its 8 unanswered questions include five of the hardest, so its perfect score is on an easier subset.
- Every model differs from the answer key most on the "needs review" cases: the single judges rarely say "not sure" and decide instead. `gpt-oss-120b` decided all three of them itself.
- Extra analysis from the saved answers: a rule where two judges must agree, and a disagreement goes to a person. `gpt-oss-120b` with `qwen3.8-27b` gave 35 correct, no copy let in, no new question blocked, 2 unclear cases decided, and 3 questions sent to a person. `gpt-oss-20b` with `qwen3.8-27b` gave 35 correct, no harmful mistake, 1 unclear decided, 4 sent to a person. Pairs with `gemini-3.5-flash-lite` gave 33 correct with no harmful mistake but 4 to 6 sent to a person.
- Limits: 40 questions is small, so a difference of one or two answers can be chance. The pairs were chosen by looking at the same 40 questions, so the best pair's score is optimistic; it needs checking on questions it has not seen.
- Commit: `Add Groq judge results`.

## 2026-10-15

### Question 2: other ways of combining judges

- The user asked whether there was a better option than two judges that must agree. Added `experiments/combine_judges.py`, which replays the saved answers (no new AI calls) under several schemes. Results are in `experiments/results/judge_combinations.json`.
- Best: two judges (`gpt-oss-120b` and `qwen3.8-27b`), and only when they disagree a referee (`gemini-3.8-flash`) is asked. 37 of 40 correct, no copy let in, no new question blocked, 2 unclear cases decided, 1 sent to a person. The referee was needed for 4 of the 40 questions, which fits its free allowance of 20 a day.
- Majority vote of three Groq models: 36 correct but one new question blocked and all three unclear cases decided: voting hides doubt.
- Cheap judge first, stronger judge only when the cheap one is unsure: 33 correct. It fails because `gemini-3.5-flash-lite` rated itself 4 or 5 out of 5 on every answer it got wrong, so its confidence is no guide.
- Limit, as before: all schemes were compared on the same 40 questions that were used to pick them, so the best score is optimistic.
- Commit: `Compare ways of combining judges`.

### Question 2: judge decided

- **Decision (D11):** two judges, `gpt-oss-120b` and `qwen3.8-27b`, and only when they disagree a referee, `gemini-3.8-flash`. The referee counts when it backs one of the judges; otherwise the question is held for a person. Chosen over two judges with every disagreement going to a person, a majority vote, a single judge, and a cheap-then-strong cascade; see `decision.md`.
- The user asked to complete Question 2 and report results, and to make sure the data built for it is of good quality, unbiased and has nothing unnecessary.
- Added `JudgePanel` to `qbank/judge.py`, which the detector uses like a single judge, with 6 tests (76 pass).
- Commit: `Add the judge panel`.

### Question 2: data audit

- Asked by the user to make sure the data we made is of good quality, unbiased and has nothing unnecessary. Checks run: label counts per kind and per corpus question; near-identical pairs inside the answer key (embedding similarity of 0.93 or more); four-word runs shared between the judge's instructions and any test question; and the commit history, which shows the labels were fixed (2026-10-11 11:35) before the judge's instructions were written (12:02) and before any judge was run.
- Removed 9 questions, with the reason recorded in the answer key's `audit` field: C04, C05, C06 and C10 tested the same text clean-up as another question; C12 was nearly the wording of corpus question Q2; C23 was the same plain rewording of Q9 as C22; C32 repeated C31's one-word trick on the same question group; C37 ("Describe an experiment to verify ...") matched a worked example in the judge's instructions, which would favour the judge; C46 was off the subject. None of them had been answered wrongly by any judge, so removing them can only lower scores.
- Added 6 questions for the thinnest kinds (variants C51 to C53, needs review C54 to C56), marked `added` because they were written after the first tests; their results are reported separately. No existing label was changed.
- The answer key now has 47 questions: 6 exact duplicates, 16 semantic duplicates, 6 variants, 13 different, 6 needs review.
- From the Amazon ML Challenge 2026 notes (asked for by the user), two lessons applied: the search stage is measured on its own because a candidate it misses cannot be recovered later, and results are reported per kind of question because the test mix is not the real-world mix (an overall score there hid about 90% of wrong picks). Nothing else from that project applied.
- All experiments were rerun on the audited key. Embeddings: `Qwen3-Embedding-0.6B` still the only local model with every partner among the nearest three (34 of 34), so D10 stands. Judges: the chosen panel, run for real, got 38 of 41 with no harmful mistake, and 6 of 6 on the added questions; D11 stands. `gemini-3.8-flash` was limited to its saved answers in this run so its daily allowance stays for the referee job.
- Commit: `Audit the answer key and rerun the experiments`.

### Question 2: completed

- **Decisions D12 to D14 were made by Claude without asking**, because the user asked to finish quickly; each is recorded in `decision.md` so the user can change it. D12: `gemini-3.5-flash-lite` writes new questions and labels concepts, so the two judges never mark their own writing. D13: the coverage summary is built from concept labels (an LLM-made syllabus plus a label per question), the same labels that drive the detector's second search route. D14: the bank is one readable JSON file, with vectors recomputed on load.
- Added `qbank/concepts.py` (syllabus and concept labeler, reusing known labels), the second search route in `qbank/search.py` and `qbank/detector.py` (up to 3 stored questions sharing the new question's concept label are shown to the judges after the 5 nearest by meaning), `qbank/bank.py` (stored questions with key-value tags that duplicate checks never read, the review list, save and load), `qbank/generator.py` (the memory-guided loop and a naive baseline for comparison), `qbank/setup.py` (builds the decided system), `qbank/__main__.py` (command line: check, generate, review, resolve, list) and `examples/run_demo.py` (end-to-end demo writing `examples/REPORT.md`).
- Tests use stand-ins for every model: 86 pass with no keys or downloads.
- Added the Question 2 README: architecture, the duplicate rule, both mechanisms, tags, technology choices and trade-offs, evaluation method and what a proper evaluation would add, limits, and how to run.
- Commit: `Complete Question 2: concept labels, bank, generator, command line and README`.

### Question 2: end-to-end demo and quality fixes

- First demo run: the assignment check gave 9 of 10 (Q8 judged a semantic duplicate of Q1 instead of "needs review"). Checking the output for quality found three problems, all fixed:
  - `gemini-3.5-flash-lite`, as labeler, gave all ten assignment questions the label "laws of reflection", and with a stricter prompt still labelled Q1 and Q3, the same question, differently. `gpt-oss-20b` labelled them consistently, so it is now the labeler (D12, revised).
  - A judge answering "needs review" without naming an existing question had its answer thrown away as unusable. "Needs review" is now usable without a named question; a duplicate or variant must still name one. Test added.
  - The referee's 20 daily requests ran out during the run, so every disagreement went to a person. `gemini-3.5-flash-lite` was added as a backup referee (D11, addition); it made no harmful mistake as referee in the replayed comparison.
- Second run: 10 of 10, but the syllabus (listed by `gemini-3.5-flash-lite`) began with general light topics, and gap-targeting steered the guided writer off the subject: two questions on quantum theory, others on luminous objects and shadows. The syllabus is now listed by `gpt-oss-120b`, whose 19 points all belong to reflection, and both the syllabus and writer prompts now say to stay inside the subject.
- A repeatability check (rerunning everything from the saved replies) found a bug: several clients for the same model each kept their own copy of the reply cache, and the last to save overwrote replies the others had saved, so reruns asked the writer again and got different questions. Fixed in `qbank/llm.py`: one shared store per cache file, merged with the file on every save. Test added.
- The saved replies were then trimmed to the ones the final experiments and demo use (superseded prompts and removed test questions dropped), and everything was rerun with all network access blocked: the demo files came out byte-for-byte identical and the judge results unchanged.
- Final, verified results: 10 of 10 on the assignment check. Naive writer: 10 checked, 6 accepted, 2 rejected as repeats, 2 held, 5 concepts. Memory-guided writer: 13 checked, 10 accepted, 0 rejected, 3 held, 8 concepts, 2 rounds. All generated questions are on reflection. Answer key: the panel 38 of 41 with no harmful mistake, unchanged. Results are in `examples/REPORT.md`, `examples/demo_results.json` and `examples/demo_bank.json`.
- Honest notes recorded in the README: Q8 is borderline (it changed with the set of questions shown to the judges); one run each is not a rate; 3 of 13 guided questions were held, all applied versions of existing ones, which is the first thing to improve.
- Tests: 89 pass.
- Commit: `Fix labelling, referee and syllabus quality; add the final demo results`.

### Open

- The deadline: the user said on 2026-10-11 they had four days, so it may be today. Asked the user for the exact date; no answer yet.
- Question 1 has not been started.
- Nothing has been pushed.
