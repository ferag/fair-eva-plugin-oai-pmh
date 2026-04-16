"""Compatibility contract tests between plugin and FAIR EVA core."""

import importlib.metadata as metadata
import subprocess
import sys
import tempfile

import pytest

from fair_eva.api.evaluator import EvaluatorBase
from fair_eva.api import rda
from fair_eva.plugin.oai_pmh.plugin import Plugin

from tests.helpers import run_plugin_smoke


def test_plugin_class_is_importable():
    """Protect against packaging/import regressions across core updates."""

    assert Plugin is not None


def test_plugin_is_evaluatorbase_subclass():
    """Protect the inheritance contract expected by FAIR EVA core."""

    assert issubclass(Plugin, EvaluatorBase)


def test_plugin_instantiation_builds_metadata_dataframe(monkeypatch, tracking_config):
    """Ensure constructor keeps producing coherent ``self.metadata`` shape.

    The test patches metadata retrieval to keep runtime deterministic while still
    executing the constructor flow expected by the core.
    """

    plugin, _ = run_plugin_smoke(tracking_config, monkeypatch)

    assert not plugin.metadata.empty
    assert {"metadata_schema", "element", "text_value", "qualifier"}.issubset(
        set(plugin.metadata.columns)
    )


def test_smoke_path_keeps_core_expected_flow(monkeypatch, tracking_config):
    """Run a representative smoke path to catch API drift early."""

    _, results = run_plugin_smoke(tracking_config, monkeypatch)

    # Core indicators return ``(points, message_list)`` tuples.
    for indicator, result in results.items():
        assert isinstance(result, tuple), f"{indicator} no devolvió una tupla"
        assert len(result) == 2, f"{indicator} debe devolver (points, messages)"


def test_collect_plugins_works_in_editable_installs():
    """Regression test for Python 3.12 editable namespace path issues.

    ``rda.collect_plugins()`` must not crash with:
    ``NotADirectoryError: MultiplexedPath only supports directories``.
    """

    plugin_list = rda.collect_plugins()
    assert "oai_pmh" in plugin_list


def test_editable_install_imports_plugin_outside_repo():
    """Regression test: plugin must be importable from non-repo CWD."""

    try:
        metadata.distribution("fair-eva-plugin-oai-pmh")
    except metadata.PackageNotFoundError:
        pytest.skip("This test requires the plugin distribution to be installed")

    code = (
        "import fair_eva.plugin; "
        "from fair_eva.api import rda; "
        "plugins = rda.collect_plugins(); "
        "assert 'oai_pmh' in plugins"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tempfile.gettempdir(),
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, (
        "Editable install does not expose plugin correctly outside repo.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
