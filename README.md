# fair-eva-plugin-oai-pmh

FAIR-eva 'oai-pmh' plugin.

## Installation

Use [pip](https://pip.pypa.io/en/stable/) to install `fair-eva-plugin-oai-pmh` package.

```bash
pip install git+https://github.com/IFCA-Advanced-Computing/fair_eva_plugin_oai_pmh
```

## Compatibility test suite

This repository includes a compatibility-oriented pytest suite focused on:

- plugin/core contract stability,
- runtime config compatibility using a generic `TrackingConfigParser`,
- OAI-PMH flows with mocked HTTP responses,
- representative FAIR indicators with controlled metadata.

Run locally:

```bash
python -m pip install -e . --no-deps
python -m pip install -r test-requirements.txt
pytest -q
```

Notes for local testing
-----------------------

- The compatibility suite is exercised in CI using Python 3.10 and 3.12. Local
	runs should use a matching Python version (3.10 or 3.12) to avoid
	dependency incompatibilities observed with newer interpreters.

- Recommended quick workflow (uses a Python 3.12 virtual environment):

```bash
# create venv with python3.12
python3.12 -m venv .venv-py312
. .venv-py312/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install "fair_eva @ git+https://github.com/IFCA-Advanced-Computing/FAIR_eva@main"
python -m pip install -e . --no-deps
python -m pip install -r test-requirements.txt
pytest -q
```

If you don't have `python3.12` available, use one of the versions in the CI
matrix (3.10 or 3.12) to reproduce results reliably.

## CI matrix against FAIR EVA refs

GitHub Actions workflow `.github/workflows/compatibility-tests.yml` installs FAIR EVA core from configurable refs.

- By default, it runs against `main`.
- To test multiple refs, define repository variable `FAIR_EVA_REFS_JSON` with JSON array syntax, for example:

```text
["main", "refs/tags/vX.Y.Z"]
```

## Usage

After installation, the plugin is automatically loaded by the [FAIR-eva API server](https://github.com/IFCA-Advanced-Computing/FAIR_eva) as a namespace package.

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[GPL-3.0-or-later](LICENSE)
