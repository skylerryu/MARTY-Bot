import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel


load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


class AnswerGrade(BaseModel):
    correct: bool
    confidence: float
    reason: str


async def test_llm():
    response = await client.responses.create(
        model="gpt-5.4-nano",
        input="Reply with exactly: M.A.R.T.Y. LLM connected"
    )

    return response.output_text


async def grade_answer_with_llm(
    question: str,
    correct_answer: str,
    student_answer: str
) -> AnswerGrade:

    response = await client.responses.parse(
        model="gpt-5.4-mini",

        input=[
            {
                "role": "system",
                    "content": (
                        "You are grading short-answer responses for an EMT education bot. "
                        "Compare the student's answer to the instructor's official answer. "
                        "Judge semantic and medical equivalence, NOT exact wording. "

                        "IMPORTANT GRADING RULES: "

                        "Do not infer missing units. If the answer involves a dose, rate, "
                        "measurement, duration, concentration, or other quantity requiring units, "
                        "the student's response must provide sufficient units or context to make "
                        "the answer medically unambiguous, unless the question explicitly asks "
                        "for only the numerical value. "

                        "For example, if the expected answer is 100-120 compressions per minute, "
                        "'120 compressions per minute', '120/min', and '120 cpm' may be correct, "
                        "but '120' by itself is incomplete because the unit is unspecified. "

                        "If the official answer specifies a numerical range, a value within that "
                        "range may be correct when the question asks for an acceptable value. "
                        "If the question specifically asks for the entire range, the student "
                        "must provide the range. "

                        "Accept equivalent terminology, standard medical abbreviations, minor "
                        "spelling errors, and equivalent unit notation when the meaning remains "
                        "unambiguous. "

                        "Accept concise answers when they correctly identify the requested medical "
                        "concept. A student does not need to answer in a complete sentence. "

                        "For example, if the official answer is 'inhibits platelet aggregation', "
                        "answers such as 'antiplatelet', 'prevents platelet aggregation', "
                        "'keeps platelets from sticking together', or 'reduces platelet clumping' "
                        "should be considered medically equivalent. "

                        "Judge whether the student's response answers what the QUESTION asks, "
                        "not whether it contains all the words in the official answer. "

                        "Do not invent missing information or assume what the student intended."
                    )
            },
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\n"
                    f"Official answer:\n{correct_answer}\n\n"
                    f"Student answer:\n{student_answer}"
                )
            }
        ],

        text_format=AnswerGrade
    )

    return response.output_parsed