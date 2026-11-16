from math import gcd

import numpy as np
from scipy.signal import resample_poly


def resample_audio(
    audio: np.ndarray,
    original_rate: int,
    target_rate: int = 16000
) -> np.ndarray:

    audio = np.asarray(
        audio,
        dtype=np.float32
    ).reshape(-1)

    if original_rate <= 0 or target_rate <= 0:
        raise ValueError("Invalid sample rate.")

    if original_rate == target_rate:
        return audio.copy()

    divisor = gcd(original_rate, target_rate)

    up = target_rate // divisor
    down = original_rate // divisor

    result = resample_poly(
        audio,
        up=up,
        down=down
    )

    return np.asarray(result, dtype=np.float32)