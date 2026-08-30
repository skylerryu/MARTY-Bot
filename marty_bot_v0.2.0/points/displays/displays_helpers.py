# ==================================================
# PROGRESS BAR
# ==================================================


def build_progress_bar(
    progress_percent: float,
    length: int = 12,
) -> str:
    """
    Build a fixed-width visual progress bar.

    Example:
    ▰▰▰▰▰▱▱▱▱▱▱▱
    """

    progress_percent = max(
        0.0,
        min(progress_percent, 100.0),
    )

    filled = int(
        progress_percent / 100 * length
    )

    empty = length - filled

    return (
        "▰" * filled
        + "▱" * empty
    )