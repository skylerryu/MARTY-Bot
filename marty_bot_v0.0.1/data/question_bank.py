import json
import random

from pathlib import Path


QUESTIONS_FILE = Path(__file__).with_name("questions.json")


def load_questions():
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def get_question_by_id(question_id: int):
    questions = load_questions()

    for question in questions:
        if question["id"] == question_id:
            return question

    return None


def get_random_question(category: str | None = None):
    questions = load_questions()

    active_questions = [
        question
        for question in questions
        if question.get("active", True)
    ]

    if category is not None:
        active_questions = [
            question
            for question in active_questions
            if question["category"] == category
        ]

    if not active_questions:
        return None

    return random.choice(active_questions)


def add_question(
    category: str,
    question_text: str,
    correct_answer: str,
    explanation: str
):
    questions = load_questions()

    if questions:
        new_id = max(
            question["id"]
            for question in questions
        ) + 1
    else:
        new_id = 1

    new_question = {
        "id": new_id,
        "category": category,
        "question": question_text,
        "answer": correct_answer,
        "explanation": explanation,
        "active": True
    }

    questions.append(new_question)

    with open(QUESTIONS_FILE, "w", encoding="utf-8") as file:
        json.dump(
            questions,
            file,
            indent=4,
            ensure_ascii=False
        )

    return new_question