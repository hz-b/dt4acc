from typing import Sequence


def hcm_coefficients(device_index: Sequence[int]) -> Sequence[float]:
    device_index = tuple(device_index)
    if device_index[1] in (2, 7):
        return 0.88 * 4.070e-4, 0.5
    elif device_index[1] in (1, 8):
        return 0.95 * 4.070e-4, 0.5
    elif device_index in {(5, 3), (5, 6)}:
        return 0.6329 * 9.500e-4 * 0.45, 0.2030
    elif device_index in {(5, 5), (7, 4)}:
        return 0.5046 * 10.250e-4 * 0.45, 0.2030
    elif device_index[1] in (3, 6):
        return 0.7667 * 9.500e-4, 0.2030
    elif device_index[1] in (4, 5):
        return 0.6156 * 10.250e-4, 0.2030
    elif device_index[1] == 10:
        return 1.0753 * 0.2e-4, 0.2030
    else:
        raise ValueError(
            f"Unknown device {device_index} (checking only {device_index[1]}"
        )

    assert 0, "Should not reach here"
