# dt4acc

**Digital Twins for Accelerators (dt4acc)** is a Python package developed by the Helmholtz-Zentrum Berlin (HZB) to support digital twin modeling and control of particle accelerators.

## Features

- **Modular Architecture**: Clear separation between source code components.
- **Modern Python Packaging**: Uses `pyproject.toml` for dependency management and build configuration.
- **Open Source**: Licensed under the GNU General Public License v3.0 (GPL-3.0), encouraging collaboration and transparency.

## Installation

Clone and install the package:

```bash
git clone https://github.com/hz-b/dt4acc.git
cd dt4acc
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

> **Note:** The `-e` flag installs the package in editable mode, which is useful during development.

## Usage

Import the package in your scripts:

```python
import dt4acc
```

### Running the Digital Twin with EPICS

#### Required Environment Variables

- `DT4ACC_PREFIX`: Prefix for all EPICS variables (e.g., `MyTwin`).
- `MONGODB_URL`: MongoDB URI (e.g., `mongodb://localhost:47017/bessyii`).
- `MONGODB_DB`: MongoDB database name (default: `bessyii`).

### MongoDB Setup

You can either install MongoDB manually or run it inside a container.

#### Option A: Manual MongoDB Installation

Follow the [lat2db](https://github.com/hz-b/lat2db) instructions to import your lattice into MongoDB.

#### Option B: MongoDB Container

Use a pre-built container from [bact-containers](https://github.com/hz-b/bact-containers/blob/main/recipes/mongo-container.sdef):

```bash
cd /twin_containers_data/bin
apptainer run -B data/db/:/data/db ./mongo-container.sif
```

This binds your host's data directory to the container's MongoDB volume.

#### Importing Data into MongoDB

With the container running, restore collections individually:

```bash
mongorestore --port 47017 --db bessyii --collection machines data/to_import/machines.bson
mongorestore --port 47017 --db bessyii --collection accelerator.setup data/to_import/accelerator.bson
mongorestore --port 47017 --db bessyii --collection bpm.config data/to_import/bpm_config.bson
mongorestore --port 47017 --db bessyii --collection bpm.offset data/to_import/bpm_offset.bson
```

Or restore the full database:

```bash
mongorestore --port 47017 --db bessyii data/to_import/bessyii
```

### Running the Twin

Set the environment variables:

```bash
export MONGODB_URL=mongodb://localhost:47017/bessyii
export MONGODB_DB=bessyii
export DT4ACC_PREFIX=MyTwin
```

> Defaults: If unset, the prefix will default to `Anonym`, MongoDB URL to `localhost:27017`, and DB name to `bessyii`.

Start the twin server:

```bash
python src/dt4acc/custom_epics/ioc/server.py
```

### Interact with the Twin

Use EPICS command-line tools:

```bash
pvlist
pvlist <hash>
pvget <pv_name>
pvput <pv_name> <value>
```

### Containerized Twin

You can also run the twin entirely in a container. See [bessyii_specifics.rst](https://github.com/hz-b/bact-containers/blob/main/doc/bessyii_specifics.rst) for more details.
