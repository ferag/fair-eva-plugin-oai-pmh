"""FAIR EVA plugin package path compatibility helpers.

Keeping this module as a regular package avoids Python 3.12 editable-install
issues with ``importlib.resources.files("fair_eva.plugin")`` while still
allowing additional plugin distributions to contribute subpackages.
"""

from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)
