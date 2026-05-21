def vcm_coefficients(device: tuple[int, int]) -> tuple[float, float]:
    if device[1] in (1, 8):
        return 2 * 1.0802 * 1.711e-4, 0.5
    if device[1] in (2, 7):
        return 2.0 * 0.8473 * 1.711e-4, 0.5
    if device[1] in (4, 5):
        return -2.5 * 3.0e-4, 0.2030
    if device[1] == 10:
        return 0.3532e-4, 0.2030
    assert 0, "Should never reach here"