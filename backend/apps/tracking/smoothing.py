SMOOTHING_ALPHA = 0.4


def smooth(prev, current):
    if not prev:
        return current

    return (
        prev[0] * (1 - SMOOTHING_ALPHA) + current[0] * SMOOTHING_ALPHA,
        prev[1] * (1 - SMOOTHING_ALPHA) + current[1] * SMOOTHING_ALPHA,
    )
