from config import QUESTION_ATTEMPT_LIMIT


question_attempts = {}


def record_question_attempt(
    guild_id: int,
    channel_id: int,
    question_id: int,
    posted_at: str,
    user_id: int
):
    key = (
        guild_id,
        channel_id,
        question_id,
        posted_at,
        user_id
    )

    attempts_used = question_attempts.get(
        key,
        0
    )

    if attempts_used >= QUESTION_ATTEMPT_LIMIT:
        return False, attempts_used

    attempts_used += 1
    question_attempts[key] = attempts_used

    return True, attempts_used


def clear_question_attempts_for_channel(
    guild_id: int,
    channel_id: int
):
    keys_to_remove = [
        key
        for key in question_attempts
        if (
            key[0] == guild_id
            and key[1] == channel_id
        )
    ]

    for key in keys_to_remove:
        del question_attempts[key]