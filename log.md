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

### Open

- Next decisions: exactly what counts as a duplicate, then the exact local embedding model, the LLMs, the coverage summary and storage.
- Nothing has been pushed.
