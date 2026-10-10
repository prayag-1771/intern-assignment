# Question 2: generating questions without duplicates

Solution for [Question 2](../questions/question-2-duplicate-questions.md). Work in progress; the full write-up of architecture, algorithms, choices and trade-offs will replace this note.

## Layout so far

- `data/corpus.json`: the ten test questions from the assignment with their expected labels.
- `qbank/`: the Python package.
- `experiments/`: small measurements behind each technology choice, with saved results.
