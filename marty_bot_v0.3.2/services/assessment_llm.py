import asyncio
import json
import os

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    InternalServerError,
    RateLimitError,
)

from points.mechanics.patient_assessment.assessment_config import (
    ASSESSMENT_LLM_MAX_CONCURRENT_REQUESTS,
    ASSESSMENT_LLM_RETRY_ATTEMPTS,
    ASSESSMENT_LLM_RETRY_BASE_SECONDS,
    ASSESSMENT_SCENARIO_MODEL,
    ASSESSMENT_TURN_MODEL,
)
from points.mechanics.patient_assessment.assessment_models import (
    AssessmentTurnResult,
    GeneratedAssessmentScenario,
)


load_dotenv()


client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


_assessment_llm_semaphore = asyncio.Semaphore(
    ASSESSMENT_LLM_MAX_CONCURRENT_REQUESTS
)


# ==================================================
# RETRY / CONCURRENCY
# ==================================================


async def _parse_with_retry(**kwargs):
    last_error = None

    for attempt in range(
        1,
        ASSESSMENT_LLM_RETRY_ATTEMPTS + 1,
    ):
        try:
            async with _assessment_llm_semaphore:
                return await client.responses.parse(
                    **kwargs
                )

        except (
            RateLimitError,
            APITimeoutError,
            APIConnectionError,
            InternalServerError,
        ) as error:
            last_error = error

            if attempt >= ASSESSMENT_LLM_RETRY_ATTEMPTS:
                raise

            await asyncio.sleep(
                ASSESSMENT_LLM_RETRY_BASE_SECONDS
                * (2 ** (attempt - 1))
            )

    if last_error is not None:
        raise last_error

    raise RuntimeError(
        "Assessment LLM retry loop ended unexpectedly."
    )


# ==================================================
# USAGE
# ==================================================


def _usage_dict(response) -> dict:
    usage = getattr(
        response,
        "usage",
        None,
    )

    if usage is None:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }

    input_tokens = int(
        getattr(
            usage,
            "input_tokens",
            0,
        )
        or 0
    )

    output_tokens = int(
        getattr(
            usage,
            "output_tokens",
            0,
        )
        or 0
    )

    total_tokens = int(
        getattr(
            usage,
            "total_tokens",
            input_tokens + output_tokens,
        )
        or (
            input_tokens
            + output_tokens
        )
    )

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


# ==================================================
# GENERATE DAILY SCENARIO
# ==================================================


async def generate_daily_assessment_scenario(
    scenario_type: str,
    rubric_text: str,
    conditional_rubric_text: str,
) -> tuple[
    GeneratedAssessmentScenario,
    dict,
]:
    """
    Generate one frozen patient scenario.

    The generated object is persisted before students
    can begin. Every student therefore encounters the
    same underlying patient truth for the day.
    """

    system_prompt = (
        "You create realistic EMT-B patient-assessment "
        "practice scenarios for M.A.R.T.Y., an educational "
        "Discord bot. You are creating the hidden master "
        "scenario, not interacting with a student yet.\n\n"

        "The assessment is graded from the instructor rubric "
        "provided below. Build enough hidden facts for a proctor "
        "or simulated patient to answer every reasonable question "
        "the student may ask. Include relevant negatives as well "
        "as positives.\n\n"

        "IMPORTANT RULES:\n"
        "1. The dispatch text must NOT reveal the final diagnosis.\n"
        "2. The patient's facts must remain internally consistent.\n"
        "3. Use adult EMT-B scenarios. OB scenarios should use an "
        "adult pregnant patient.\n"
        "4. Do not use real patient names or identifying data.\n"
        "5. Keep the scenario within EMT-B training scope and the "
        "provided class rubric.\n"
        "6. Every fact must have a stable key and a source. Use "
        "patient for interview answers, proctor/physical_exam for "
        "observations, monitor for device/vital results, dispatch "
        "for dispatch information, and partner when appropriate.\n"
        "7. treatment_effects must be deterministic. If a treatment "
        "changes SpO2, symptoms, mental status, lung sounds, etc., "
        "provide explicit updated facts.\n"
        "8. applicable_conditional_keys may ONLY contain keys from "
        "the conditional-key list below and only when that action "
        "is genuinely relevant to this patient.\n"
        "9. critical_required_actions should only contain rubric "
        "keys whose omission would leave a major airway, breathing, "
        "hemorrhage, or shock problem untreated.\n"
        "10. For trauma scenarios choose 1-3 relevant regions from: "
        "head, neck, chest, abdomen, pelvis, lower_extremities, "
        "upper_extremities, back.\n"
        "11. For airway scenarios follow the sequence represented "
        "by the airway-management rubric: unresponsive patient, "
        "weak pulse, apnea, vomit requiring suction, OPA/BVM, then "
        "deterioration requiring a supraglottic airway.\n"
        "12. The opening_scene may contain what an EMT could observe "
        "on arrival, but do not volunteer hidden SAMPLE/OPQRST facts.\n"
    )

    user_prompt = (
        f"SCENARIO TYPE:\n{scenario_type}\n\n"
        "APPLICABLE RUBRIC CATALOG:\n"
        f"{rubric_text}\n\n"
        "CONDITIONAL RUBRIC KEYS THAT MAY BE ACTIVATED:\n"
        f"{conditional_rubric_text}\n\n"
        "Create today's frozen scenario."
    )

    response = await _parse_with_retry(
            model=ASSESSMENT_SCENARIO_MODEL,
            input=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            text_format=(
                GeneratedAssessmentScenario
            ),
        )

    parsed = response.output_parsed

    if parsed is None:
        raise RuntimeError(
            "The scenario LLM returned no structured scenario."
        )

    return parsed, _usage_dict(response)


# ==================================================
# PROCESS ONE STUDENT TURN
# ==================================================


async def interpret_assessment_turn(
    scenario: dict,
    patient_state: dict,
    rubric_text: str,
    earned_keys: set[str],
    recent_turns: list[dict],
    student_input: str,
    elapsed_seconds: float,
) -> tuple[
    AssessmentTurnResult,
    dict,
]:
    """
    Interpret a student's natural-language statement and
    generate the patient/proctor response in one LLM call.

    The model identifies possible rubric events, but Python
    remains authoritative for scoring and validates every key.
    """

    history_text = "\n\n".join(
        (
            f"TURN {turn['turn_number']}\n"
            f"Student: {turn['student_input']}\n"
            f"MARTY ({turn['response_role']}): "
            f"{turn['marty_response']}"
        )
        for turn in recent_turns
    )

    if not history_text:
        history_text = "(no previous turns)"

    system_prompt = (
        "You are M.A.R.T.Y. acting as both an EMT practical "
        "exam proctor and the simulated patient. This is a "
        "practice assessment.\n\n"

        "You receive a FROZEN hidden patient scenario. Never "
        "change its facts and never invent findings that are not "
        "supported by the scenario/current patient state. If the "
        "student asks for information that truly is not represented, "
        "say that no additional information is provided rather than "
        "inventing it.\n\n"

        "RESPONSE BEHAVIOR:\n"
        "- If the student interviews the patient, answer naturally "
        "as the patient.\n"
        "- If the student performs an exam maneuver, asks for a vital, "
        "uses a monitor, or performs something the patient could not "
        "report, respond as the proctor/monitor.\n"
        "- If both occur, use response_role=mixed and clearly separate "
        "the patient and proctor information.\n"
        "- Reveal ONLY information the student's stated actions or "
        "questions would reasonably obtain. Do not volunteer SAMPLE, "
        "OPQRST, focused findings, or the diagnosis.\n"
        "- Do NOT coach the student during the attempt. Do not say what "
        "they forgot, what they should do next, whether they earned "
        "points, or whether their assessment is good/bad.\n\n"

        "RUBRIC INTERPRETATION:\n"
        "- rubric_keys must contain only keys from the supplied rubric.\n"
        "- Award a key only when the student's CURRENT statement actually "
        "performs/verbalizes that action. Do not infer unstated actions.\n"
        "- Equivalent wording and common EMT abbreviations count.\n"
        "- Do not repeat already-earned keys merely because they are in "
        "conversation history.\n"
        "- treatment_keys must be a subset of rubric_keys and only include "
        "treatments the student actually initiates/administers/assists.\n"
        "- transport_called is true only if the student initiates/calls for "
        "transport, begins transport, or clearly directs transport.\n"
        "- handoff_report_given is true only if the student actually gives "
        "a transfer/receiving report containing meaningful patient information.\n"
        "- priority_decision is high or low only when the student actually "
        "states a transport priority; otherwise none.\n"
        "- field_impression_text should contain the student's stated field "
        "impression if one was actually stated.\n"
        "- dangerous_action should be true only for a clearly dangerous or "
        "inappropriate intervention, not merely an incomplete assessment. "
        "Set dangerous_action_confidence from 0.0 to 1.0.\n"
        "- unacceptable_affect should be true only for clearly abusive, "
        "disrespectful, or unacceptable interaction with the patient or "
        "personnel. Set unacceptable_affect_confidence from 0.0 to 1.0.\n"
    )

    context = {
        "scenario": scenario,
        "current_patient_state": patient_state,
        "earned_rubric_keys": sorted(earned_keys),
        "elapsed_seconds": round(
            elapsed_seconds,
            1,
        ),
        "recent_transcript": history_text,
        "applicable_rubric": rubric_text,
        "student_input": student_input,
    }

    response = await _parse_with_retry(
            model=ASSESSMENT_TURN_MODEL,
            input=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        context,
                        ensure_ascii=False,
                    ),
                },
            ],
            text_format=AssessmentTurnResult,
        )

    parsed = response.output_parsed

    if parsed is None:
        raise RuntimeError(
            "The assessment LLM returned no structured turn."
        )

    return parsed, _usage_dict(response)
