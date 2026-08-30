import json
import random
from pathlib import Path
from threading import Lock


# ==================================================
# QUESTION BANK PATHS
# ==================================================


QUESTION_BANK_DIR = (
    Path(__file__).with_name(
        "question_bank"
    )
)

METADATA_PATH = (
    QUESTION_BANK_DIR
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


_question_bank_lock = Lock()


# ==================================================
# CATEGORY PATH
# ==================================================


def _get_category_path(
    category: str,
) -> Path:
    """
    Return the JSON file belonging to a
    question category.
    """

    if category not in CATEGORY_NAMES:

        raise ValueError(
            f"Unknown question category: {category}"
        )

    return (
        QUESTION_BANK_DIR
        / f"{category}.json"
    )


# ==================================================
# JSON HELPERS
# ==================================================


def _load_json_file(
    path: Path,
):
    """
    Load JSON data from disk.
    """

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
    """
    Save JSON data atomically.

    A temporary file is written first so an
    interrupted write is less likely to damage
    the real question-bank file.
    """

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
# QUESTION BANK SETUP
# ==================================================


def _ensure_question_bank_exists():
    """
    Make sure the question-bank folder,
    metadata file, and category files exist.
    """

    QUESTION_BANK_DIR.mkdir(
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
    """
    Load information about the question bank.

    metadata.json currently stores the next
    permanent global question ID.
    """

    _ensure_question_bank_exists()

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
    """
    Save question-bank metadata.
    """

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
    """
    Load all questions in one category.

    The category is represented by the filename,
    so it is added to each question in memory.
    """

    _ensure_question_bank_exists()

    category_path = (
        _get_category_path(
            category
        )
    )

    questions = _load_json_file(
        category_path
    )

    if not isinstance(
        questions,
        list,
    ):

        raise ValueError(
            f"{category_path.name} must "
            "contain a JSON list."
        )

    loaded_questions = []

    for question in questions:

        if not isinstance(
            question,
            dict,
        ):

            raise ValueError(
                f"{category_path.name} contains "
                "an invalid question."
            )

        loaded_question = dict(
            question
        )

        loaded_question["category"] = (
            category
        )

        loaded_questions.append(
            loaded_question
        )

    return loaded_questions


def _save_category_questions(
    category: str,
    questions: list[dict],
):
    """
    Save all questions in one category.

    The category field is removed from the
    stored JSON because the filename already
    identifies the category.
    """

    category_path = (
        _get_category_path(
            category
        )
    )

    questions_to_save = []

    for question in questions:

        stored_question = dict(
            question
        )

        stored_question.pop(
            "category",
            None,
        )

        questions_to_save.append(
            stored_question
        )

    _save_json_file(
        category_path,
        questions_to_save,
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

        cleaned_answer = (
            answer.strip()
        )

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
# HIGHEST QUESTION ID
# ==================================================


def _get_highest_question_id() -> int:
    """
    Return the highest permanent question ID
    currently stored in the entire bank.

    This protects against metadata.json becoming
    accidentally lower than an existing ID.
    """

    highest_id = 0

    for category in CATEGORY_NAMES:

        questions = (
            _load_category_questions(
                category
            )
        )

        for question in questions:

            question_id = int(
                question["id"]
            )

            highest_id = max(
                highest_id,
                question_id,
            )

    return highest_id


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

    The question is written to its category
    file and receives a globally unique
    permanent numeric ID.
    """

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
    # SAVE QUESTION
    # ==================================================


    with _question_bank_lock:

        metadata = (
            _load_metadata()
        )

        highest_question_id = (
            _get_highest_question_id()
        )

        question_id = max(
            int(
                metadata["next_id"]
            ),
            highest_question_id + 1,
        )

        new_question = {
            "id": question_id,
            "category": category,
            "question": question_text,
            "accepted_answers": cleaned_answers,
            "explanation": explanation,
            "active": True,
        }

        category_questions = (
            _load_category_questions(
                category
            )
        )

        category_questions.append(
            new_question
        )

        _save_category_questions(
            category=category,
            questions=category_questions,
        )

        metadata["next_id"] = (
            question_id + 1
        )

        _save_metadata(
            metadata
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

    for category in CATEGORY_NAMES:

        questions = (
            _load_category_questions(
                category
            )
        )

        for question in questions:

            if (
                question["id"]
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
    Return questions from every category.

    By default, inactive questions are not
    returned.
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

    return [
        question
        for question in all_questions
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

    category can restrict selection to one
    category.

    excluded_ids can prevent reserved questions
    from being selected.
    """

    if excluded_ids is None:
        excluded_ids = set()


    # ==================================================
    # LOAD QUESTIONS
    # ==================================================


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


    # ==================================================
    # FILTER
    # ==================================================


    eligible_questions = []

    for question in questions:

        if not question.get(
            "active",
            True,
        ):
            continue

        if (
            question["id"]
            in excluded_ids
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
    stored across all categories.
    """

    return len(
        get_all_questions(
            active_only=active_only
        )
    )
