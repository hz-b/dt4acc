# dt4acc bootstrap refactor

This is a first-pass refactor of the ALS bootstrap script into small modules:

- `config.py` for aliases and family wiring
- `yellow_pages_builder.py` for yellow pages input
- `liaison_builder.py` for liaison LUTs and PV views
- `translator_builder.py` for translation LUTs
- `bootstrap.py` for orchestration

The runtime behavior is intended to stay close to the original script while making the setup easier to test and extend.
