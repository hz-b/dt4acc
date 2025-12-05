import logging
import at

logger = logging.getLogger("enrich-at")


def insert_scraper(lattice, index, copy=True):
    save_length = lattice.cell_length
    logger.debug(
        "Inserting elements at index %s: element names around %s",
        index,
        [elem.FamName for elem in lattice[index - 5 : index + 5]],
    )

    lattice = lattice.copy()
    drift = lattice.pop(index)
    drift_start = at.Drift(family_name=drift.FamName + "_bs", length=drift.Length / 4.0)
    aperture_entry = at.Aperture(
        family_name="test_scaper_entry", limits=[-50e-3, 50e-3, -50e-3, 50e-3]
    )
    collimator = at.Collimator(
        family_name="test_scraper",
        length=drift.Length / 2.0,
        limits=[-50e-3, 50e-3, -50e-3, 50e-3],
    )
    aperture_exit = at.Aperture(
        family_name="test_scaper_exit", limits=[-50e-3, 50e-3, -50e-3, 50e-3]
    )
    drift_end = at.Drift(family_name=drift.FamName + "_ds", length=drift.Length / 4.0)
    elems = drift.insert(
        [
            (0.125, drift_start),
            (0.25, aperture_entry),
            (0.5, collimator),
            (0.75, aperture_exit),
            (0.875, drift_end),
        ]
    )

    for elem in elems[::-1]:
        # print(elem.FamName)
        # print([elem.FamName for elem in bessyii_lattice[198:205]])
        lattice.insert(index, elem)

    logger.debug(
        "Inserted elements at index %s: element names around %s",
        index,
        [elem.FamName for elem in lattice[index - 5 : index + 5]],
    )

    assert (
        lattice.cell_length == save_length
    ), f"Lattice length changed from {save_length} -> {lattice.cell_length}"

    return lattice
