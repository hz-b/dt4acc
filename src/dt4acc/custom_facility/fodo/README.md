# FODO digital twin — building a twin from just a lattice file

This documents the pipeline used to turn `resources/fodo_lattice.json` — a
bare AT (accelerator toolbox) lattice and nothing else — into a running
digital twin. It's written up as a general recipe: follow the same five
steps for any new facility that starts from nothing but a lattice file.

## Starting point

All we had going in: `resources/fodo_lattice.json`, an [atjson v1]
lattice (the format `at.Lattice.save_json()` produces) — a flat list of
elements, each with `FamName`, `Class`, `PassMethod`, `PolynomA`/
`PolynomB`, `Length`, etc. Nothing facility-specific existed yet: no
magnet database, no power-converter naming, no liaison/translator
config, no launcher script.

Everything below is generated *from* that one file (plus a naming
convention for power converters, since the lattice itself doesn't know
about hardware).

## Prerequisites

- `dt4acc-lib` importable (`pip install -e ../dt4acc-lib --no-deps` if
  you're working from a sibling checkout rather than a released
  version — see [Gotcha: multipole property naming](#gotcha-multipole-property-naming-b1a1-not-x_kicky_kick-or-b0a0)
  below for why the checked-out version matters here).
- `bson`, `PyYAML`, `jsons` (already project dependencies).

## Pipeline overview

```
fodo_lattice.json (atjson)
        │  json2accelerator_setup_fodo.py
        ▼
accelerator_setup.json                 (magnet DB: Quadrupole/Sextupole/Steerer, name/pc/k)
        │  create_fodo_yellow_pages.py
        ▼
fodo_yellow_pages_lookup_table.yml     (named families: quadrupoles, steerers, ...)
        │  create_fodo_liaison_and_translator.py
        ▼
fodo_liaison_manager_forward/inverse_lookup_table.yml   (lattice-property <-> device-property)
fodo_translation_service_lookup_table.yml               (unit conversion per mapping)
        │  liasion_translator_setup.py (loader, no generation)
        ▼
run_fodo_twin.py                        (starts the EPICS soft-IOC twin)
```

All the generator scripts live in `scripts/` and are idempotent — safe
to rerun after editing the lattice or a naming convention; each one
reads its inputs fresh and overwrites its output.

### Step 1 — magnet database (`accelerator_setup.json`)

Script: `scripts/json2accelerator_setup_fodo.py`

Walks `fodo_lattice.json`'s elements and picks out the ones that are
driven by a power converter — `Quadrupole`, `Sextupole`, and
`Multipole` (FODO's combined H/V correctors) — producing one entry per
controllable device:

```json
{"_id": {"$oid": "..."}, "type": "Quadrupole", "name": "QF_001",
 "magnetic_strength": 1.258, "pc": "QF_001_PC", "k": 1.258}
```

- `Quadrupole`/`Sextupole` elements map 1:1 to entries (`k` taken from
  `K` / `PolynomB[2]`).
- Each `Multipole` element (FODO's corrector, e.g. `COR_001`) becomes
  **two** `Steerer` entries — `HCOR_001` (from `PolynomB[0]`) and
  `VCOR_001` (from `PolynomA[0]`) — since the two planes are driven by
  independent power converters. There is **no** separate entry for the
  `Multipole` host itself; see the gotcha below.
- `Drift`/`Bend`/`RFCavity`/`Monitor` elements are skipped — they have
  no power converter in this schema (matches the "standard" facility's
  `accelerator_setup.json`, which this script's output schema mirrors).

Run: `python3 src/dt4acc/custom_facility/fodo/scripts/json2accelerator_setup_fodo.py`
Writes: `src/dt4acc/custom_epics/data/fodo/accelerator_setup.json`

### Step 2 — yellow pages (`fodo_yellow_pages_lookup_table.yml`)

Script: `scripts/create_fodo_yellow_pages.py`

Groups the magnet DB into named families (`quadrupoles`, `sextupoles`,
`steerers`, `horizontal_steerers`, `vertical_steerers`, plus
`horizontal_steerers_host`/`vertical_steerers_host` — the underlying
`Multipole` element name each steerer acts on, e.g. `COR_001` for both
`HCOR_001` and `VCOR_001`). `cavities` comes straight from the lattice
(`RFCavity` elements aren't in `accelerator_setup.json` either — no PC
of their own). Mirrors `create_yellow_pages_lut_from_config()` in
`scripts/bessyii/create_managers_input.py`, but is derived directly
from `accelerator_setup.json` since FODO has no separate
`magnets.yaml`/`power_converters.yaml` input config.

Run: `python3 src/dt4acc/custom_facility/fodo/scripts/create_fodo_yellow_pages.py`
Writes: `resources/created/fodo_yellow_pages_lookup_table.yml`

### Step 3 — liaison manager + translator tables

Script: `scripts/create_fodo_liaison_and_translator.py`

Builds the three remaining lookup tables that `dt4acc_lib`'s
`LiaisonManager`/`TranslatorService` need — mirrors
`build_liaison_manager_lut()` / `build_translator_manager_lut()` in
`scripts/bessyii/create_managers_input.py`:

- **forward**: lattice property → device property(ies), e.g.
  `QF_001.main_strength → QF_001_PC.set_current`.
- **inverse**: device property → lattice property(ies) (the reverse,
  plus readback-only entries like `..._PC.rdbk_current`).
- **translator**: the actual unit-conversion coefficients per mapping.
  FODO has no calibration-curve input yet, so every PC↔strength
  conversion is `PolynomCoefficients([0.0, 1.0], ...)` (identity) —
  replace with real curves once FODO gets calibration data.

Also adds the facility-independent bookkeeping every twin needs
(`tune`, `orbit`, `twiss`, `track`, `survey` — copied verbatim from the
BESSY II generator, since those aren't lattice-specific).

Verifies both liaison tables (`.verify()` — no duplicate keys) and
round-trips everything through `jsons` before writing, exactly like
the BESSY II script does.

Run: `python3 src/dt4acc/custom_facility/fodo/scripts/create_fodo_liaison_and_translator.py`
Writes: `resources/created/fodo_liaison_manager_forward_lookup_table.yml`,
`fodo_liaison_manager_inverse_lookup_table.yml`,
`fodo_translation_service_lookup_table.yml`

### Step 4 — loader module

`liasion_translator_setup.py` — not a generator, just loads the three
YAML files above (plus the yellow pages) into `YellowPages`,
`LiaisonManager`, `TranslatorService` objects via `load_managers()`.
Straight port of `custom_facility/bessyii/liasion_translator_setup.py`
pointed at `custom_facility/fodo/resources/created`.

### Step 5 — twin launcher

`run_fodo_twin.py` — port of `custom_facility/bessyii/run_bessyii_twin.py`.
The one facility-specific piece is how the lattice gets loaded:

```python
from dt4acc.core.bl.handle_lattice import lattice_loader

filename = resources.files("dt4acc").joinpath(
    "custom_facility/fodo/resources/fodo_lattice.json"
)
lattice_loader.set_lattice_file(filename)
acc = lattice_loader.load()   # at.load_json() under the hood — no
                               # factory/transform step needed, since
                               # fodo_lattice.json is already atjson v1
```

BESSY II needs a custom `lat2db` factory step because its source file
(`bessy2_storage_ring_reflat.json`) isn't atjson. If your lattice
*is* already atjson v1 (as `at.Lattice.save_json()` produces), skip
that entirely and use `lattice_loader` as above.

Everything else (PV setup, controller, orbit server, IOC startup) is
identical to the BESSY II launcher.

## Regenerating everything

Order matters — each step reads the previous step's output:

```bash
python3 src/dt4acc/custom_facility/fodo/scripts/json2accelerator_setup_fodo.py
python3 src/dt4acc/custom_facility/fodo/scripts/create_fodo_yellow_pages.py
python3 src/dt4acc/custom_facility/fodo/scripts/create_fodo_liaison_and_translator.py
```

Run this whenever `fodo_lattice.json` changes, or after editing any of
the three generator scripts.

## Gotchas found while wiring this up

### Combined-function correctors: steerer vs. multipole

`COR_001` is **one** AT `Multipole` lattice element carrying both a
horizontal kick (`PolynomB[0]`) and a vertical kick (`PolynomA[0]`).
`HCOR_001`/`VCOR_001` are the two **steerers** — the actual
power-converter-driven correctors — that act on it. Terminology that
matters here: the *steerer* is the corrector; the *multipole* is just
the magnet/lattice element it sits on. There is no separate
`accelerator_setup.json` entry for the multipole host itself — it has
no power converter of its own — but both steerers' liaison-manager
entries correctly point back at the **same** lattice element name
(`COR_001`), distinguished only by property (see next gotcha).
Verify with:

```python
lm.inverse(DevicePropertyID("HCOR_001", "main_strength"))
# -> [LatticeElementPropertyID("COR_001", "B1")]
lm.inverse(DevicePropertyID("VCOR_001", "main_strength"))
# -> [LatticeElementPropertyID("COR_001", "A1")]
```

### Multipole property naming: `B1`/`A1`, not `x_kick`/`y_kick` or `B0`/`A0`

AT's `PolynomA`/`PolynomB` arrays are 0-indexed, but `dt4acc_lib`'s
simulator backend (`ElementProxyFactory`) names multipole properties
using the **European convention** (dipole = order 1, quadrupole =
order 2, ...). So the corrector's dipole term at Python index
`PolynomB[0]`/`PolynomA[0]` is addressed as **`B1`/`A1`** — not `B0`/
`A0` (order 0 doesn't exist in this convention; `dt4acc_lib` asserts
against it) and not `x_kick`/`y_kick` (that route goes through the
element's `KickAngle` attribute instead, which our `Multipole`-class
correctors don't carry — AT only builds `KickAngle` for `at.Corrector`
elements, not generic `at.Multipole`).

`dt4acc_lib`'s generic `Multipole` property handler
(`pyat_simulator/element_properties/multipole.py`) already writes
straight into the `PolynomB`/`PolynomA` arrays — it just wasn't wired
up for order 1. Fixed in the sibling `dt4acc-lib` checkout
(`pyat_simulator/proxies/proxy_factory.py`): the multipole property
range was widened from `range(2, 20)` to `range(1, 20)`, so `B1`/`A1`
are now resolvable and write directly to `PolynomB[0]`/`PolynomA[0]`.
**If you're pulling in a released `dt4acc-lib` rather than this
sibling checkout, confirm that widened range made it in** — otherwise
`B1`/`A1` won't resolve and you'll see the same
`can't resolve ... known properties: [...]` error this session started
from.

### EPICS string length limit (39 characters)

`fodo_lattice.json`'s `UUID` field is `"<FamName>_<hex hash>"`. For
7-character `FamName`s (`BPM_xxx`, `COR_xxx`) that came out to 40
characters — one over what an EPICS string PV (`DBF_STRING`) can hold
(39). `custom_epics/ioc/view.py` used to silently truncate uids with
`[:39]` when pushing them to `survey`/`track`/`twiss` waveform PVs,
which risks turning distinct uids into duplicates. Fixed both ends:

- **Source data**: `scripts/shorten_fodo_uuids.py` truncated the hash
  suffix from 32→16 hex characters in `fodo_lattice.json` (still
  effectively collision-free for a lattice this size), bringing the
  max UUID length down to 24. Rerun it if new elements ever push a
  `FamName` long enough to matter again.
- **`view.py`**: replaced the `[:39]` truncation with
  `assert_epics_string_lengths()`, which raises a clear `ValueError`
  naming the offending value(s) instead of silently cutting them —
  so a future over-length uid fails loudly at the source rather than
  corrupting data downstream.

## File map

| File | Role |
|---|---|
| `resources/fodo_lattice.json` | Input: the AT lattice (atjson v1). Not generated by anything here. |
| `scripts/json2accelerator_setup_fodo.py` | Lattice → magnet DB |
| `scripts/create_fodo_yellow_pages.py` | Magnet DB → yellow pages |
| `scripts/create_fodo_liaison_and_translator.py` | Yellow pages + magnet DB → liaison/translator tables |
| `scripts/shorten_fodo_uuids.py` | One-off/rerunnable fix for over-length element UUIDs |
| `resources/created/fodo_yellow_pages_lookup_table.yml` | Generated (step 2) |
| `resources/created/fodo_liaison_manager_forward_lookup_table.yml` | Generated (step 3) |
| `resources/created/fodo_liaison_manager_inverse_lookup_table.yml` | Generated (step 3) |
| `resources/created/fodo_translation_service_lookup_table.yml` | Generated (step 3) |
| `liasion_translator_setup.py` | Loads the generated YAML into `YellowPages`/`LiaisonManager`/`TranslatorService` |
| `run_fodo_twin.py` | Starts the twin (EPICS soft-IOC) |
| `../../custom_epics/data/fodo/accelerator_setup.json` | Generated (step 1) — lives outside this folder since it's `custom_epics`-owned data, matching the `standard` facility's layout |
