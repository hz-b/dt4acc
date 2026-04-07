import json
from pathlib import Path
from typing import Any


class AcceleratorConfig:
    def __init__(self):
        self.accelerator_setup_file: str | None = None
        self.accelerator_lattice_file: str | None = None
        self._accelerator_setup: list[dict[str, Any]] | None = None

    def get_accelerator_setup(self) -> list[dict[str, Any]] | None:
        if self._accelerator_setup is None and self.accelerator_setup_file is not None:
            accelerator_setup_path = Path(self.accelerator_setup_file)
            with accelerator_setup_path.open() as fp:
                self._accelerator_setup = json.load(fp)
        return self._accelerator_setup

    def get_lattice_file(self) -> str | None:
        return self.accelerator_lattice_file


accelerator_config = AcceleratorConfig()
