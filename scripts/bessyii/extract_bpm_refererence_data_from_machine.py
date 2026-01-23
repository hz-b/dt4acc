"""Read Beam position monitor configuration data from Orbit process variables

The produced file needs then to be placed in appropriate data source
"""
import asyncio
from dataclasses import asdict
from itertools import zip_longest
import json
import jsons
import aioca

from dt4acc.core.model.bpm_description import BPMDescriptionCollection, BPMDescription


async def main():
    names_ = "ORBITCC:rdBpmNames"
    spos_ = "ORBITCC:rdSPos"

    names, spos = await asyncio.gather(*[aioca.caget(id_) for id_ in [names_, spos_]])

    def is_used(name: str) -> bool:
        """
        Some extra places in vector are marked as SBPM. These are not used
        """
        if name[:3] == "BPM":
            return True
        return False

    r = BPMDescriptionCollection(
        col=[
            BPMDescription(name=n, longitudinal_position=s, used=False)
            for n, s in zip_longest(names, spos)
        ]
    )

    tmp = jsons.dump(asdict(r))
    with open("bpm_cfg_as_in_machine.json", "wt") as fp:
        json.dump(tmp, fp, indent=4)


if __name__ == "__main__":
    asyncio.run(main())
