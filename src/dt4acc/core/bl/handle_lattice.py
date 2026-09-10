from pathlib import Path
import os

import at


class LatticeLoader:
    def __init__(self, path: Path=None):
        self.path = path

    def set_lattice_file(self, filename: Path):
        """

        Todo: should one check that the filename exists?
        """
        self.path = filename

    def load(self):
        if self.path is None:
            filename = os.environ.get("DT4ACC_LATTICE_FILE")
            if filename:
                self.path = Path(filename)
        if self.path is None:
            raise ValueError(
                "default_lattice_filename not set"
                " — set handle_lattice.default_lattice_filname before main()"
            )
        return _load_lattice(self.path)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.path!r})"


def _load_lattice(path: Path):
    """
    Load an AT lattice from file. Supports:
      .m    — MATLAB/Octave format via at.load_m()
      .json — atjson v1 format via at.load_json()
    """
    suffix = path.suffix.lower()
    if suffix == ".json":
        return at.load_json(str(path))
    elif suffix == ".m":
        return at.load_m(path)
    else:
        raise ValueError(
            f"Unsupported lattice file format: {suffix!r}. "
            "Expected .m (MATLAB) or .json (atjson v1)."
        )


lattice_loader = LatticeLoader()

__all__ = ["lattice_loader"]
