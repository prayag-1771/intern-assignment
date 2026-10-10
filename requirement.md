# Requirements in plain terms

Working notes on what the two assignment questions ask for. The official wording is in [questions/](questions/); this file restates it simply and marks the hard parts.

Only one question is required. The plan is to do both: Question 2 first, then Question 1.

## Question 2: stop an AI from writing the same question twice

Source: [questions/question-2-duplicate-questions.md](questions/question-2-duplicate-questions.md)

### The situation

A learning app has a bank of thousands of exam questions. A teacher clicks "generate 10 more on reflection of light". The LLM has no idea what is already in the bank, so it writes "What is reflection of light?" again, or the same question in different words.

### What must be built

1. **Prevention.** Before generating, show the LLM what already exists so it writes something new. Thousands of questions cannot be pasted into one prompt (the model's context is limited), so the system must pick only the relevant ones.
2. **Detection.** A separate checker examines every new question against the bank and flags duplicates. It must not rely on prevention having worked; it is the safety net.
3. **Tags are not evidence.** Questions carry labels such as `subject=physics` or `grade=8`, and new labels can appear at any time. Two questions with different tags can still be duplicates, so the comparison must use the question text.
4. **Proof.** Show it working on exact duplicates, paraphrases and different questions, and explain how accuracy and speed would be measured.

### The hard part

"Same meaning" has three levels:

- **Exact:** "Define the reflection of light." twice, perhaps with different punctuation.
- **Paraphrase:** "What is reflection of light?" and "Define the reflection of light."
- **Close but different:** "What is the angle of reflection?" and "The angle of incidence is 30°. What is the angle of reflection?" share almost all their words, but one asks for a definition and the other for a calculation.

### Test data and expected results

| ID | Question | Expected classification |
|----|----------|-------------------------|
| Q1 | What is reflection of light? | Original |
| Q2 | Define the reflection of light. | Semantic duplicate of Q1 |
| Q3 | What do you understand by the reflection of light? | Semantic duplicate of Q1 |
| Q4 | Explain the meaning of light reflection. | Semantic duplicate of Q1 |
| Q5 | State the laws of reflection of light. | Different question |
| Q6 | What is the angle of reflection? | Different question |
| Q7 | The angle of incidence is 30°. What is the angle of reflection? | Different question |
| Q8 | What is reflection? | Potentially ambiguous; review context |
| Q9 | What is the difference between regular and diffuse reflection? | Different question |
| Q10 | Define the reflection of light. | Exact duplicate of Q2 |

### What it tests

Embeddings and search, prompt design, scaling, and honest evaluation.

## Question 1: a smart image library that can build new pictures

Source: [questions/question-1-image-catalog.md](questions/question-1-image-catalog.md)

### The situation

An app where you upload images (an apple, a cartoon boy, some shapes) and later ask for a new picture made from them.

### What must be built

1. **Catalog.** Store each image with a record describing it.
2. **Automatic detection.** On upload, find what is in the image: its name, colour, how confident the system is, and a *bounding box* (the rectangle around the object, given as x, y, width, height). It must work on both cartoon and photographic images.
3. **Manual correction.** Detection will sometimes be wrong. The user can add, edit or delete objects, and those corrections must stay until the user explicitly asks for detection to run again. The record must also show which fields the machine filled in and which the user did.
4. **Composites.** The user types "Create an image containing one red apple and one orange". The system finds those two catalog images, cuts the objects out, arranges them on a new canvas, and saves the result as a new catalog entry with its own metadata.

### The hard parts

- **Three kinds of image, one system.** Most detectors are trained on photos. They are weaker on cartoons, and they have no concept of "circle" or "red swatch" at all. One model will not cover all eight test images.
- **No AI redrawing.** The composite must use the actual stored apple, not an image generator's new apple. The LLM may only plan the layout (what goes where, how big); code does the pasting.
- **Edge cases.** Overlapping shapes, and an image with nothing detectable in it.
- **No test images are supplied.** All eight have to be made or sourced.

### Test images

| Image name | Description | Expected objects / metadata |
|------------|-------------|-----------------------------|
| `apple` | A single red apple on a white background | Object: apple; color: red; bounding box |
| `orange` | A single orange fruit on a white background | Object: orange; color: orange; bounding box |
| `boy` | A cartoon boy standing | Object: boy; clothing colors; bounding box |
| `girl` | A cartoon girl standing | Object: girl; clothing colors; bounding box |
| `shapes` | Circle, square, triangle, and rectangle | Four objects; shape labels; bounding boxes |
| `colors` | Red, blue, green, yellow, and purple color swatches | Five regions; color labels; bounding boxes |
| `apple_orange` | An apple beside an orange | Two objects; individual bounding boxes |
| `overlapping_shapes` | Overlapping colored geometric shapes | Shape labels; colors; overlapping bounding boxes |

### Test scenarios

1. Detect objects and extract their names, colors, confidence scores, and bounding boxes.
2. Manually add an object when detection misses it.
3. Edit an object's name, color, confidence, or bounding box.
4. Verify manual corrections persist until detection is explicitly rerun.
5. Generate a composite using the existing `apple` and `orange` assets.
6. Generate a composite containing a boy, a girl, and colored shapes.
7. Test overlapping objects and images containing no detectable objects.

### What it tests

System and data design (machine fields versus user fields), practical computer vision, and using an LLM as a planner instead of a generator.

## How the two compare

| | Question 2 | Question 1 |
|---|---|---|
| Size | One pipeline | Four connected parts |
| Test data | Given in full | Names only; we create it |
| Main risk | Grey-zone pairs | Detection across photos, cartoons and shapes |
| Needs a UI | No | Helpful for manual correction |

## What every submission needs

- Working code for each question attempted, each in its own directory.
- An explanation of architecture, algorithms, technology choices and trade-offs.
- Examples that demonstrate the scenarios listed in each question.
