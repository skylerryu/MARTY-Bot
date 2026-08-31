import json
import random

from pathlib import Path
from threading import Lock

from questions.q_edit_queue import (
    get_question_edit_hold_ids,
)


# ==================================================
# QUESTION BANK PATHS
# ==================================================


Q_BANK_DIR = (
    Path(__file__).with_name(
        "q_bank"
    )
)

METADATA_PATH = (
    Q_BANK_DIR
    / "metadata.json"
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


_q_bank_lock = Lock()


# ==================================================
# CATEGORY PATH
# ==================================================


def _get_category_path(
    category: str,
) -> Path:

    if category not in CATEGORY_NAMES:

        raise ValueError(
            f"Unknown question category: {category}"
        )

    return (
        Q_BANK_DIR
        / f"{category}.json"
    )


# ==================================================
# JSON HELPERS
# ==================================================


def _load_json_file(
    path: Path,
):

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(
            file
        )


def _save_json_file(
    path: Path,
    data,
):

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = (
        path.with_suffix(
            path.suffix + ".tmp"
        )
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False,
        )

        file.write(
            "\n"
        )

    temporary_path.replace(
        path
    )


# ==================================================
# SETUP
# ==================================================


def _ensure_q_bank_exists():

    Q_BANK_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not METADATA_PATH.exists():

        _save_json_file(
            METADATA_PATH,
            {
                "next_id": 1,
            },
        )

    for category in CATEGORY_NAMES:

        category_path = (
            _get_category_path(
                category
            )
        )

        if not category_path.exists():

            _save_json_file(
                category_path,
                [],
            )


# ==================================================
# METADATA
# ==================================================


def _load_metadata() -> dict:

    _ensure_q_bank_exists()

    metadata = _load_json_file(
        METADATA_PATH
    )

    if not isinstance(
        metadata,
        dict,
    ):

        raise ValueError(
            "metadata.json must contain "
            "a JSON object."
        )

    if "next_id" not in metadata:

        raise ValueError(
            "metadata.json is missing next_id."
        )

    return metadata


def _save_metadata(
    metadata: dict,
):

    _save_json_file(
        METADATA_PATH,
        metadata,
    )


# ==================================================
# CATEGORY QUESTIONS
# ==================================================


def _load_category_questions(
    category: str,
) -> list[dict]:

    _ensure_q_bank_exists()

    path = (
        _get_category_path(
            category
        )
    )

    questions = _load_json_file(
        path
    )

    if not isinstance(
        questions,
        list,
    ):

        raise ValueError(
            f"{path.name} must contain "
            "a JSON list."
        )

    loaded = []

    for question in questions:

        if not isinstance(
            question,
            dict,
        ):

            raise ValueError(
                f"{path.name} contains "
                "an invalid question."
            )

        item = dict(
            question
        )

        item["category"] = (
            category
        )

        loaded.append(
            item
        )

    return loaded


def _save_category_questions(
    category: str,
    questions: list[dict],
):

    stored_questions = []

    for question in questions:

        stored = dict(
            question
        )

        stored.pop(
            "category",
            None,
        )

        stored_questions.append(
            stored
        )

    _save_json_file(
        _get_category_path(
            category
        ),
        stored_questions,
    )


# ==================================================
# CLEAN ANSWERS
# ==================================================


def _clean_accepted_answers(
    accepted_answers: list[str],
) -> list[str]:

    cleaned = []
    seen = set()

    for answer in accepted_answers:

        value = (
            answer.strip()
        )

        if not value:
            continue

        comparison = (
            value.casefold()
        )

        if comparison in seen:
            continue

        seen.add(
            comparison
        )

        cleaned.append(
            value
        )

    return cleaned


# ==================================================
# HIGHEST QUESTION ID
# ==================================================


def _get_highest_question_id() -> int:

    highest = 0

    for category in CATEGORY_NAMES:

        questions = (
            _load_category_questions(
                category
            )
        )

        for question in questions:

            highest = max(
                highest,
                int(
                    question["id"]
                ),
            )

    return highest


# ==================================================
# ADD QUESTION
# ==================================================


def add_question(
    category: str,
    question_text: str,
    accepted_answers: list[str],
    explanation: str,
) -> dict:

    category = (
        category.strip()
    )

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

    with _q_bank_lock:

        metadata = (
            _load_metadata()
        )

        question_id = max(
            int(
                metadata["next_id"]
            ),
            _get_highest_question_id() + 1,
        )

        new_question = {
            "id": question_id,
            "category": category,
            "question": question_text,
            "accepted_answers": cleaned_answers,
            "explanation": explanation,
            "active": True,
        }

        questions = (
            _load_category_questions(
                category
            )
        )

        questions.append(
            new_question
        )

        _save_category_questions(
            category=category,
            questions=questions,
        )

        metadata["next_id"] = (
            question_id + 1
        )

        _save_metadata(
            metadata
        )

    return new_question


# ==================================================
# UPDATE QUESTION
# ==================================================


def update_question(
    question_id: int,
    question_text: str,
    accepted_answers: list[str],
) -> dict:

    question_text = (
        question_text.strip()
    )

    cleaned_answers = (
        _clean_accepted_answers(
            accepted_answers
        )
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

    with _q_bank_lock:

        for category in CATEGORY_NAMES:

            questions = (
                _load_category_questions(
                    category
                )
            )

            for index, question in enumerate(
                questions
            ):

                if (
                    int(
                        question["id"]
                    )
                    != question_id
                ):
                    continue

                updated = dict(
                    question
                )

                updated["question"] = (
                    question_text
                )

                updated[
                    "accepted_answers"
                ] = cleaned_answers

                questions[index] = (
                    updated
                )

                _save_category_questions(
                    category=category,
                    questions=questions,
                )

                return updated

    raise ValueError(
        f"Question #{question_id} "
        "was not found."
    )


# ==================================================
# GET QUESTION BY ID
# ==================================================


def get_question_by_id(
    question_id: int,
) -> dict | None:
    """
    Direct retrieval still returns a quarantined
    question.

    Admin interfaces need to be able to see and
    edit questions that are being held.
    """

    for category in CATEGORY_NAMES:

        questions = (
            _load_category_questions(
                category
            )
        )

        for question in questions:

            if (
                int(
                    question["id"]
                )
                == question_id
            ):

                return question

    return None


# ==================================================
# GET ALL QUESTIONS
# ==================================================


def get_all_questions(
    active_only: bool = True,
) -> list[dict]:
    """
    When active_only=True, questions currently
    in the edit queue are automatically excluded.
    """

    all_questions = []

    for category in CATEGORY_NAMES:

        all_questions.extend(
            _load_category_questions(
                category
            )
        )

    if not active_only:

        return all_questions

    held_ids = (
        get_question_edit_hold_ids()
    )

    return [
        question
        for question in all_questions
        if (
            question.get(
                "active",
                True,
            )
            and int(
                question["id"]
            )
            not in held_ids
        )
    ]


# ==================================================
# GET RANDOM QUESTION
# ==================================================


def get_random_question(
    category: str | None = None,
    excluded_ids: set[int] | None = None,
) -> dict | None:

    if excluded_ids is None:
        excluded_ids = set()

    held_ids = (
        get_question_edit_hold_ids()
    )

    excluded_ids = (
        set(excluded_ids)
        | held_ids
    )

    if category is not None:

        if category not in CATEGORY_NAMES:

            raise ValueError(
                f"Unknown question category: {category}"
            )

        questions = (
            _load_category_questions(
                category
            )
        )

    else:

        questions = (
            get_all_questions(
                active_only=True
            )
        )

    eligible = []

    for question in questions:

        if not question.get(
            "active",
            True,
        ):
            continue

        if (
            int(
                question["id"]
            )
            in excluded_ids
        ):
            continue

        eligible.append(
            question
        )

    if not eligible:
        return None

    return random.choice(
        eligible
    )


# ==================================================
# COUNT
# ==================================================


def get_question_count(
    active_only: bool = True,
) -> int:

    return len(
        get_all_questions(
            active_only=active_only
        )
    )