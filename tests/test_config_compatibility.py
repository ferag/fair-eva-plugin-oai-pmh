"""Generic configuration compatibility tests.

No plugin-specific ``config_schema.py`` is used. Compatibility is inferred from
real runtime reads observed by ``TrackingConfigParser``.
"""

import pytest

from tests.helpers import clone_config, format_missing, run_plugin_smoke
import importlib
from pathlib import Path
import configparser




def test_real_or_template_config_is_loadable(loaded_config_path, tracking_config):
    """Ensure at least one repository config artifact is usable in tests."""

    assert loaded_config_path.exists()
    assert tracking_config.sections()


def test_runtime_missing_keys_are_reported_clearly(monkeypatch, tracking_config):
    """Fail if smoke execution tries to read a missing runtime key.

    We remove one known runtime key to verify the instrumentation and error
    message quality. This protects against silent compatibility breakages.
    """

    broken = clone_config(tracking_config)
    broken.remove_option("oai_pmh", "terms_cv")

    with pytest.raises(KeyError):
        run_plugin_smoke(broken, monkeypatch)

    assert broken.missing, "Se esperaba al menos una clave faltante registrada"
    assert any(
        miss.section == "oai_pmh" and miss.option == "terms_cv" for miss in broken.missing
    ), f"Faltantes observados: {format_missing(broken.missing)}"


def test_unused_keys_are_reported_non_destructively(monkeypatch, tracking_config):
    """Report potentially-unused INI keys without hard failing.

    Important limitation: an unused key in this report may still be required by
    non-exercised paths. The report is intentionally soft so maintainers can
    evolve coverage before turning this into a strict assertion.
    """

    run_plugin_smoke(tracking_config, monkeypatch)

    existing = tracking_config.existing_keys()
    used = tracking_config.accessed
    potentially_unused = sorted(existing - used)

    # Soft assertion: keep CI green while making the report visible in test logs.
    print(
        "Potentially unused config keys (smoke-path dependent, non-fatal):",
        [f"{section}.{option}" for section, option in potentially_unused],
    )

    assert tracking_config.missing == set(), format_missing(tracking_config.missing)


def test_plugin_includes_core_minimal_config():
    """Ensure plugin config includes keys from core minimal config.

    The test looks for `config.ini`, `config.template.ini` or
    `config.example.ini` inside the installed `fair_eva` package. If none
    are present the test is skipped. When found, every section/option from
    the core minimal config must exist in the plugin `config` candidate.
    """

    try:
        # Use importlib.resources.files when available (py3.9+)
        try:
            from importlib import resources

            pkg_files = resources.files("fair_eva")
        except Exception:
            # Fallback: import the package and use its __file__ location
            mod = importlib.import_module("fair_eva")
            pkg_files = Path(mod.__file__).parent

        core_path = None
        for name in ("config.ini", "config.template.ini", "config.example.ini"):
            candidate = pkg_files.joinpath(name) if hasattr(pkg_files, "joinpath") else pkg_files / name
            if candidate.exists():
                core_path = candidate
                break
    except Exception:
        pytest.skip("Could not locate installed 'fair_eva' package")

    if core_path is None:
        pytest.skip("No core minimal config found in installed 'fair_eva' package")

    core_parser = configparser.ConfigParser()
    core_parser.read(core_path)

    # Load plugin candidate using helper
    from tests.helpers import load_preferred_tracking_config

    plugin_pkg = importlib.import_module("fair_eva.plugin.oai_pmh")
    # Some installs expose namespace packages without a __file__ attribute.
    # In that case fall back to the local repository layout where tests run.
    pkg_file = getattr(plugin_pkg, "__file__", None)
    if pkg_file:
        plugin_dir = Path(pkg_file).parent
    else:
        # repo root is two levels up from this test file
        repo_root = Path(__file__).resolve().parents[1]
        plugin_dir = repo_root / "fair_eva" / "plugin" / "oai_pmh"
    plugin_parser, plugin_path = load_preferred_tracking_config(plugin_dir)

    # If core provides a placeholder section named `plugin_name`, map its
    # options to this plugin's actual section name (e.g. `oai_pmh`). This
    # allows the core to ship a template section that plugins must satisfy.
    if "plugin_name" in core_parser.sections():
        # determine plugin's section name from plugin_dir (folder name)
        plugin_section_name = plugin_dir.name
        core_keys = {
            (plugin_section_name, option) for option, _ in core_parser.items("plugin_name")
        }
        mapped_from_placeholder = True
    else:
        core_keys = {(section, option) for section in core_parser.sections() for option, _ in core_parser.items(section)}
        mapped_from_placeholder = False
    plugin_keys = plugin_parser.existing_keys()
    # Log discovered keys for easier debugging in CI/local runs
    core_list = sorted(f"{s}.{o}" for s, o in core_keys)
    plugin_list = sorted(f"{s}.{o}" for s, o in plugin_keys)
    print(f"Core config path: {core_path}")
    print(f"Plugin config path: {plugin_path}")
    if mapped_from_placeholder:
        print(f"Mapped core placeholder section 'plugin_name' -> plugin section '{plugin_section_name}'")
    print(f"Core config keys ({len(core_list)}):", core_list)
    print(f"Plugin config keys ({len(plugin_list)}):", plugin_list)

    missing = sorted(f"{s}.{o}" for s, o in (core_keys - plugin_keys))
    assert not missing, (
        f"Plugin config {plugin_path} is missing keys from core config {core_path}: {missing}"
    )
