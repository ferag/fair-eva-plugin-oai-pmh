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
