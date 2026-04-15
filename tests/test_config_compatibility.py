"""Generic configuration compatibility tests.

No plugin-specific ``config_schema.py`` is used. Compatibility is inferred from
real runtime reads observed by ``TrackingConfigParser``.
"""

import pytest

from tests.helpers import clone_config, format_missing, run_plugin_smoke


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
