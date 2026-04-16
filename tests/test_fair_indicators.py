"""Minimal, stable FAIR indicator compatibility tests."""

from tests.helpers import run_plugin_smoke


def test_representative_fair_indicators_with_controlled_metadata(monkeypatch, tracking_config):
    """Validate representative F/A/I/R indicators against deterministic metadata.

    The objective is compatibility (contract stability), not exhaustive scoring.
    The test verifies that key indicator entry points still execute and produce
    points/messages in the format expected by FAIR EVA core.
    """

    _, results = run_plugin_smoke(tracking_config, monkeypatch)

    for indicator in [
        "rda_f1_01m",
        "rda_f1_02m",
        "rda_f4_01m",
        "rda_a1_01m",
        "rda_i1_01m",
        "rda_r1_1_01m",
    ]:
        points, messages = results[indicator]
        assert isinstance(points, (int, float))
        assert isinstance(messages, list)
        assert messages, f"{indicator} debe devolver al menos un mensaje"
