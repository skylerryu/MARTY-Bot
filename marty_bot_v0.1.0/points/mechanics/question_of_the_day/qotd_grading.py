from services.llm import grade_answer_with_llm

from points.mechanics.question_of_the_day.qotd_config import (
    QOTD_GRADING_CONFIDENCE_THRESHOLD,
)


# ==================================================
# QOTD GRADING
# ==================================================


async def grade_qotd_answer(
    question: str,
    accepted_answers: list[str],
    student_answer: str,
) -> dict:
    """
    Grade a student's QoTD answer using
    M.A.R.T.Y.'s existing LLM grader.

    The instructor-provided accepted answers
    remain the authoritative answer key.
    """

    # The existing LLM grader expects one
    # correct_answer string.
    #
    # If the instructor supplied multiple
    # acceptable formulations, present all
    # of them as valid reference answers.

    correct_answer = (
        "\n".join(
            f"- {answer}"
            for answer in accepted_answers
        )
    )

    grade = await grade_answer_with_llm(
        question=question,
        correct_answer=correct_answer,
        student_answer=student_answer,
    )

    # --------------------------------------------------
    # DEVELOPMENT LOGGING
    # --------------------------------------------------

    print(
        "\n"
        "QoTD LLM Grade\n"
        "------------------------------\n"
        f"Student answer: {student_answer}\n"
        f"Correct: {grade.correct}\n"
        f"Confidence: {grade.confidence}\n"
        f"Reason: {grade.reason}\n"
    )

    # --------------------------------------------------
    # LOW CONFIDENCE
    # --------------------------------------------------

    if (
        grade.confidence
        < QOTD_GRADING_CONFIDENCE_THRESHOLD
    ):

        return {
            "status": "uncertain",
            "correct": None,
            "confidence": grade.confidence,
            "reason": grade.reason,
        }

    # --------------------------------------------------
    # CONFIDENT GRADE
    # --------------------------------------------------

    return {
        "status": (
            "correct"
            if grade.correct
            else "incorrect"
        ),
        "correct": grade.correct,
        "confidence": grade.confidence,
        "reason": grade.reason,
    }