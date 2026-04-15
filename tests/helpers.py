"""Reusable helpers for compatibility tests.

The goal of this module is to keep the compatibility suite readable and portable
across FAIR EVA plugins. The helpers deliberately avoid plugin-specific schemas
and instead observe real runtime configuration access patterns.
"""

from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from fair_eva.plugin.oai_pmh.plugin import Plugin


@dataclass(frozen=True)
class MissingAccess:
    """Represents a missing runtime configuration access.

    We keep section/option as a normalized pair so the test failure message can
    clearly list *exactly* what runtime lookup failed.
    """

    section: str
    option: str


class TrackingSectionProxy:
    """A proxy over ``ConfigParser`` sections that records runtime usage.

    ``EvaluatorBase`` and plugin code mostly use ``config[section][option]``.
    Wrapping the section object allows us to track those lookups without
    introducing plugin-specific required-key lists.
    """

    def __init__(self, parser: "TrackingConfigParser", section: str):
        self._parser = parser
        self._section = section

    def __getitem__(self, option: str) -> str:
        self._parser.accessed.add((self._section, option))
        try:
            return self._parser._raw_section(self._section)[option]
        except KeyError:
            self._parser.missing.add(MissingAccess(self._section, option))
            raise

    def get(self, option: str, fallback=None):
        self._parser.accessed.add((self._section, option))
        section = self._parser._raw_section(self._section)
        if option in section:
            return section[option]
        self._parser.missing.add(MissingAccess(self._section, option))
        return fallback


class TrackingConfigParser(configparser.ConfigParser):
    """ConfigParser that tracks runtime configuration usage.

    Why this exists:
    - We want compatibility checks based on *actual execution*, not on a manual
      ``config_schema.py`` list that can drift from code behavior.
    - Missing options are recorded when runtime access fails.
    - Accessed options are recorded to report potentially-unused keys.

    Limitation intentionally documented for maintainers:
    - A key reported as unused is only "unused in the exercised smoke path".
      It may still be valid for other execution paths.
    """

    def __init__(self):
        super().__init__()
        self.accessed: set[tuple[str, str]] = set()
        self.missing: set[MissingAccess] = set()

    def _raw_section(self, section: str):
        return super().__getitem__(section)

    def __getitem__(self, section: str):
        # We proxy section access so option reads can be tracked consistently.
        return TrackingSectionProxy(self, section)

    def get(self, section, option, *, raw=False, vars=None, fallback=configparser._UNSET):
        self.accessed.add((section, option))
        try:
            return super().get(section, option, raw=raw, vars=vars, fallback=fallback)
        except (configparser.NoOptionError, configparser.NoSectionError):
            self.missing.add(MissingAccess(section, option))
            raise

    def existing_keys(self) -> set[tuple[str, str]]:
        return {
            (section, option)
            for section in self.sections()
            for option in super().__getitem__(section)
        }


def plugin_config_candidates(plugin_dir: Path) -> list[Path]:
    """Return ordered config candidates.

    Priority rule for compatibility checks:
    1) ``config.ini``
    2) ``config.template.ini``
    3) ``config.example.ini``
    """

    return [
        plugin_dir / "config.ini",
        plugin_dir / "config.template.ini",
        plugin_dir / "config.example.ini",
    ]


def load_preferred_tracking_config(plugin_dir: Path) -> tuple[TrackingConfigParser, Path]:
    """Load the best available INI file into a tracking parser."""

    parser = TrackingConfigParser()
    for candidate in plugin_config_candidates(plugin_dir):
        if candidate.exists():
            parser.read(candidate)
            return parser, candidate
    raise FileNotFoundError("No config.ini/config.template.ini/config.example.ini found")


def make_sample_metadata() -> pd.DataFrame:
    """Controlled metadata used by smoke and indicator tests.

    The DataFrame intentionally includes terms mapped by several core indicators
    (F/A/I/R) so compatibility tests can fail early if the core API contract
    changes (for example, expected columns or access patterns).
    """

    rows = [
        ["{http://purl.org/dc/elements/1.1/}", "identifier", "https://doi.org/10.1234/example", None],
        ["{http://purl.org/dc/elements/1.1/}", "title", "Compatibility test record", None],
        ["{http://purl.org/dc/elements/1.1/}", "rights", "CC-BY-4.0", None],
        ["{http://purl.org/dc/elements/1.1/}", "access", "open", None],
        ["{http://purl.org/dc/elements/1.1/}", "subject", "http://id.loc.gov/authorities/subjects/sh85026371", None],
        ["{http://purl.org/dc/elements/1.1/}", "relation", "https://example.org/related", None],
    ]
    return pd.DataFrame(rows, columns=["metadata_schema", "element", "text_value", "qualifier"])


def run_plugin_smoke(config: configparser.ConfigParser, monkeypatch, metadata_df=None) -> tuple[Plugin, dict]:
    """Execute a reusable smoke path.

    We monkeypatch ``Plugin.get_metadata`` to avoid network calls and keep tests
    deterministic. This is instrumentation, not behavior change: the purpose is
    to check plugin/core API compatibility under controlled metadata.
    """

    if metadata_df is None:
        metadata_df = make_sample_metadata()

    monkeypatch.setattr(Plugin, "get_metadata", lambda self: metadata_df.copy())

    # Core indicator rda_i1_01m performs live vocabulary lookups by default.
    # We patch it to keep the compatibility suite offline and deterministic.
    monkeypatch.setattr(
        "fair_eva.api.evaluator.ut.check_controlled_vocabulary",
        lambda value: (f"Mocked CV validation for {value}", value),
    )

    plugin = Plugin(
        item_id="10.1234/example",
        api_endpoint="https://example.org/oai",
        config=config,
        name="oai_pmh",
    )

    # Run a representative subset of indicators to trigger config and metadata
    # paths used by core decorators and plugin contract.
    results = {
        "rda_f1_01m": plugin.rda_f1_01m(),
        "rda_f1_02m": plugin.rda_f1_02m(),
        "rda_f4_01m": plugin.rda_f4_01m(),
        "rda_a1_01m": plugin.rda_a1_01m(),
        "rda_i1_01m": plugin.rda_i1_01m(),
        "rda_r1_1_01m": plugin.rda_r1_1_01m(),
    }
    return plugin, results


def clone_config(parser: configparser.ConfigParser) -> TrackingConfigParser:
    """Create a mutable copy preserving tracking behavior for mutation tests."""

    cloned = TrackingConfigParser()
    for section in parser.sections():
        cloned.add_section(section)
        for option, value in parser.items(section):
            cloned.set(section, option, value)
    return cloned


def format_missing(missing: Iterable[MissingAccess]) -> str:
    """Human friendly ``section.option`` formatter for assertion messages."""

    return ", ".join(sorted(f"{m.section}.{m.option}" for m in missing))
