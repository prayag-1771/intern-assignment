"""The question bank and the generation loop, with stand-in models so no key or download is needed."""

from qbank.bank import QuestionBank
from qbank.concepts import ConceptLabel
from qbank.detector import DuplicateDetector
from qbank.generator import ALREADY_ASKED_SHOWN, QuestionGenerator, generate_naively
from qbank.judge import Judge
from tests.test_detector import StandInModel, WordEmbedder


class KeywordLabeler:
    def label(self, question):
        concept = "laws of reflection" if "law" in question.lower() else "definition of reflection"
        return ConceptLabel(concept, "state")


class ScriptedJudgeModel:
    """Says 'semantic_duplicate' of Q1 for any question containing 'meant by', otherwise 'different'."""

    def ask_json(self, system, user):
        new = user.rsplit("New question:\n", 1)[1]
        if "meant by" in new:
            return {"label": "semantic_duplicate", "matches": ["Q1"], "reason": "Rewords Q1.", "confidence": 5}
        if "polished" in new:
            return {"label": "needs_review", "matches": ["Q1"], "reason": "Looser than Q1.", "confidence": 3}
        return {"label": "different", "matches": [], "reason": "New.", "confidence": 5}


class ScriptedWriter:
    def __init__(self, rounds):
        self._rounds = list(rounds)
        self.prompts = []

    def ask_json(self, system, user):
        self.prompts.append(user)
        return {"questions": [{"question": q, "concept": "claimed"} for q in self._rounds.pop(0)]}


def _bank():
    bank = QuestionBank(WordEmbedder())
    bank.add("What is reflection of light?", {"grade": "8"}, "definition of reflection", "define", "Q1")
    bank.add("State the laws of reflection of light.", {"grade": "9"}, "laws of reflection", "state", "Q5")
    return bank


def _generator(bank, writer):
    detector = DuplicateDetector(bank.index, Judge(ScriptedJudgeModel()), KeywordLabeler())
    return QuestionGenerator(writer, bank, detector, "reflection of light", ["definition of reflection", "laws of reflection", "lateral inversion"])


def test_tags_filter_questions_but_play_no_part_in_duplicate_checks():
    bank = _bank()
    detector = DuplicateDetector(bank.index, Judge(StandInModel({"label": "different", "matches": []})))

    assert [q.id for q in bank.filter(grade="8")] == ["Q1"]
    # Same text, different tags: still an exact duplicate.
    assert detector.check("what is reflection of light").label == "exact_duplicate"


def test_held_questions_stay_out_of_the_bank_until_a_person_decides(tmp_path):
    bank = _bank()
    held = bank.hold("What happens when light falls on a polished surface?", note="Looser than Q1.")
    assert held.status == "held" and len(bank.index) == 2

    bank.resolve(held.id, is_new=True)
    assert held.status == "accepted" and len(bank.index) == 3

    path = tmp_path / "bank.json"
    bank.save(path)
    reloaded = QuestionBank.load(path, WordEmbedder())
    assert [q.id for q in reloaded.accepted()] == ["Q1", "Q5", held.id]
    assert reloaded.coverage()["definition of reflection"] == 1


def test_generation_accepts_new_rejects_repeats_holds_unclear_and_feeds_back():
    bank = _bank()
    writer = ScriptedWriter([
        ["What is meant by reflection of light?", "What is lateral inversion?", "What happens when light falls on a polished surface?"],
        ["Why does a plane mirror invert left and right?", "Give one use of a periscope."],
    ])

    attempts = _generator(bank, writer).generate(wanted=2, spare=1)

    assert [(a.round, a.outcome) for a in attempts] == [(1, "rejected"), (1, "accepted"), (1, "held"), (2, "accepted"), (2, "not checked")]
    assert [q.text for q in bank.held()] == ["What happens when light falls on a polished surface?"]
    # Round 2's prompt tells the writer what was rejected and why.
    assert '"What is meant by reflection of light?": semantic duplicate of "What is reflection of light?"' in writer.prompts[1]
    # The detector labels the concept itself; the writer's claim is not stored.
    assert all(q.concept != "claimed" for q in bank.accepted())
    assert attempts[1].detection.concept.concept == "definition of reflection"


def test_prompt_shows_coverage_gaps_and_a_bounded_list_of_existing_questions():
    bank = _bank()
    for n in range(30):
        bank.add(f"Extra question number {n} about mirrors?", concept="plane mirrors")
    prompt = _generator(bank, ScriptedWriter([])).build_prompt(3, [])

    assert "- plane mirrors: 30" in prompt
    assert "- lateral inversion (0 so far)" in prompt
    listed = prompt.split("Questions already in the bank")[1].strip().splitlines()[1:]
    assert len(listed) == ALREADY_ASKED_SHOWN


def test_naive_baseline_sees_only_the_subject():
    bank = _bank()
    writer = ScriptedWriter([["What is meant by reflection of light?", "Name two uses of plane mirrors."]])
    detector = DuplicateDetector(bank.index, Judge(ScriptedJudgeModel()), KeywordLabeler())

    attempts = generate_naively(writer, bank, detector, "reflection of light", 2)

    assert [a.outcome for a in attempts] == ["rejected", "accepted"]
    assert writer.prompts == ["Subject: reflection of light\nWrite 2 questions."]
    assert bank.questions[attempts[1].stored_id].tags["source"] == "generated-naively"
