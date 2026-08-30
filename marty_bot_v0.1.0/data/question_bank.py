import json
import random
from pathlib import Path
from threading import Lock


# ==================================================
# QUESTION BANK FILE
# ==================================================


QUESTIONS_PATH = Path(__file__).with_name(
    "questions.json"
)


# ==================================================
# QUESTION CATEGORIES
# ==================================================


CATEGORY_NAMES = {
    "random_nremt": "Random NREMT Question",
    "cpr_airway": "CPR / Airway",
    "cardiac": "Cardiac",
    "neurological": "Neurological",
    "anaphylaxis": "Anaphylaxis",
    "acute_abdomen": "Acute Abdomen",
    "ob_labor": "OB / Labor",
    "trauma": "Trauma",
    "cet_fun_fact": "CET Fun Fact",
}


# ==================================================
# FILE LOCK
# ==================================================


_question_bank_lock = Lock()


# ==================================================
# EMPTY BANK
# ==================================================


def _empty_question_bank() -> dict:
    """
    Return the structure used for a new
    question bank.
    """

    return {
        "next_id": 1,
        "questions": [],
    }


# ==================================================
# ENSURE FILE EXISTS
# ==================================================


def _ensure_question_bank_exists():
    """
    Create questions.json if it does not
    already exist.
    """

    if QUESTIONS_PATH.exists():
        return

    _save_question_bank(
        _empty_question_bank()
    )


# ==================================================
# LOAD BANK
# ==================================================


def _load_question_bank() -> dict:
    """
    Load the complete question bank from disk.
    """

    _ensure_question_bank_exists()

    with QUESTIONS_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:

        bank = json.load(
            file
        )

    if not isinstance(bank, dict):

        raise ValueError(
            "questions.json does not contain "
            "a valid question bank."
        )

    if "next_id" not in bank:

        raise ValueError(
            "questions.json is missing next_id."
        )

    if "questions" not in bank:

        raise ValueError(
            "questions.json is missing questions."
        )

    if not isinstance(
        bank["questions"],
        list,
    ):

        raise ValueError(
            "questions.json questions must "
            "be a list."
        )

    return bank


# ==================================================
# SAVE BANK
# ==================================================


def _save_question_bank(
    bank: dict,
):
    """
    Save the complete question bank to disk.

    A temporary file is written first so an
    interrupted write is less likely to damage
    the main question bank.
    """

    temporary_path = (
        QUESTIONS_PATH.with_suffix(
            ".tmp"
        )
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            bank,
            file,
            indent=4,
            ensure_ascii=False,
        )

        file.write(
            "\n"
        )

    temporary_path.replace(
        QUESTIONS_PATH
    )


# ==================================================
# CLEAN ACCEPTED ANSWERS
# ==================================================


def _clean_accepted_answers(
    accepted_answers: list[str],
) -> list[str]:
    """
    Remove blank and duplicate accepted
    answers.
    """

    cleaned_answers = []

    seen_answers = set()

    for answer in accepted_answers:

        cleaned_answer = answer.strip()

        if not cleaned_answer:
            continue

        comparison_answer = (
            cleaned_answer.casefold()
        )

        if comparison_answer in seen_answers:
            continue

        seen_answers.add(
            comparison_answer
        )

        cleaned_answers.append(
            cleaned_answer
        )

    return cleaned_answers


# ==================================================
# ADD QUESTION
# ==================================================


def add_question(
    category: str,
    question_text: str,
    accepted_answers: list[str],
    explanation: str,
) -> dict:
    """
    Add a new question to the permanent
    M.A.R.T.Y. question bank.

    The question receives the next permanent
    numeric question ID.
    """

    category = category.strip()

    question_text = (
        question_text.strip()
    )

    explanation = (
        explanation.strip()
    )

    cleaned_answers = (
        _clean_accepted_answers(
            accepted_answers
        )
    )


    # ==================================================
    # VALIDATION
    # ==================================================


    if category not in CATEGORY_NAMES:

        raise ValueError(
            f"Unknown question category: {category}"
        )

    if not question_text:

        raise ValueError(
            "Question text cannot be empty."
        )

    if not cleaned_answers:

        raise ValueError(
            "At least one accepted answer "
            "must be provided."
        )

    if not explanation:

        raise ValueError(
            "Explanation cannot be empty."
        )


    # ==================================================
    # ADD TO BANK
    # ==================================================


    with _question_bank_lock:

        bank = _load_question_bank()

        question_id = int(
            bank["next_id"]
        )

        new_question = {
            "id": question_id,
            "category": category,
            "question": question_text,
            "accepted_answers": cleaned_answers,
            "explanation": explanation,
            "active": True,
        }

        bank["questions"].append(
            new_question
        )

        bank["next_id"] = (
            question_id + 1
        )

        _save_question_bank(
            bank
        )

    return new_question


# ==================================================
# GET QUESTION BY ID
# ==================================================


def get_question_by_id(
    question_id: int,
) -> dict | None:
    """
    Retrieve a question using its permanent
    question ID.
    """

    bank = _load_question_bank()

    for question in bank["questions"]:

        if question["id"] == question_id:
            return question

    return None


# ==================================================
# GET ALL QUESTIONS
# ==================================================


def get_all_questions(
    active_only: bool = True,
) -> list[dict]:
    """
    Return all questions in the bank.

    By default, inactive questions are not
    returned.
    """

    bank = _load_question_bank()

    if not active_only:

        return list(
            bank["questions"]
        )

    return [
        question
        for question in bank["questions"]
        if question.get(
            "active",
            True,
        )
    ]


# ==================================================
# GET RANDOM QUESTION
# ==================================================


def get_random_question(
    category: str | None = None,
    excluded_ids: set[int] | None = None,
) -> dict | None:
    """
    Select a random active question.

    category can restrict the selection to a
    particular question category.

    excluded_ids can prevent reserved questions
    from being selected.

    The QoTD reservation system will use this
    later to prevent scheduled QoTD questions
    from appearing as speed questions.
    """

    if excluded_ids is None:
        excluded_ids = set()

    questions = get_all_questions(
        active_only=True
    )

    eligible_questions = []

    for question in questions:

        if question["id"] in excluded_ids:
            continue

        if (
            category is not None
            and question["category"] != category
        ):
            continue

        eligible_questions.append(
            question
        )

    if not eligible_questions:
        return None

    return random.choice(
        eligible_questions
    )


# ==================================================
# GET QUESTION COUNT
# ==================================================


def get_question_count(
    active_only: bool = True,
) -> int:
    """
    Return the number of questions currently
    stored in the bank.
    """

    return len(
        get_all_questions(
            active_only=active_only
        )
    )