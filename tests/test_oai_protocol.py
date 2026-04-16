"""OAI-PMH protocol compatibility tests without real network access."""

from types import SimpleNamespace
import xml.etree.ElementTree as ET

from fair_eva.plugin.oai_pmh.plugin import Plugin


OAI_NS = "http://www.openarchives.org/OAI/2.0/"


VALID_LIST_METADATA_FORMATS = f"""
<OAI-PMH xmlns=\"{OAI_NS}\">
  <ListMetadataFormats>
    <metadataFormat>
      <metadataPrefix>oai_dc</metadataPrefix>
      <metadataNamespace>http://www.openarchives.org/OAI/2.0/oai_dc/</metadataNamespace>
    </metadataFormat>
  </ListMetadataFormats>
</OAI-PMH>
""".strip()

VALID_GET_RECORD = f"""
<OAI-PMH xmlns=\"{OAI_NS}\" xmlns:oai_dc=\"http://www.openarchives.org/OAI/2.0/oai_dc/\" xmlns:dc=\"http://purl.org/dc/elements/1.1/\">
  <GetRecord>
    <record>
      <metadata>
        <oai_dc:dc>
          <dc:identifier>https://doi.org/10.1234/example</dc:identifier>
          <dc:title>Mocked record</dc:title>
          <dc:rights>CC-BY-4.0</dc:rights>
          <dc:access>open</dc:access>
          <dc:subject>http://id.loc.gov/authorities/subjects/sh85026371</dc:subject>
          <dc:relation>https://example.org/related</dc:relation>
        </oai_dc:dc>
      </metadata>
    </record>
  </GetRecord>
</OAI-PMH>
""".strip()

ERROR_GET_RECORD = f"""
<OAI-PMH xmlns=\"{OAI_NS}\">
  <error code=\"idDoesNotExist\">No matching identifier</error>
</OAI-PMH>
""".strip()


def _response(body: str, status_code: int = 200):
    """Tiny response stub used to mock requests.get."""

    return SimpleNamespace(text=body, status_code=status_code)


def _mock_requests_get(monkeypatch, resolver):
    """Patch ``requests.get`` in plugin module with URL-aware resolver.

    We patch at module level so every helper (oai_request, oai_check_record_url,
    oai_get_metadata) sees the same deterministic behavior.
    """

    def fake_get(url, verify=False, allow_redirects=False):  # noqa: ARG001
        return resolver(url)

    monkeypatch.setattr("fair_eva.plugin.oai_pmh.plugin.requests.get", fake_get)


def test_oai_metadata_formats_parses_valid_response(monkeypatch):
    """Protect metadata format parsing expected by get_metadata flow."""

    base = "https://example.org/oai"

    def resolver(url):
        if url == f"{base}?verb=ListMetadataFormats":
            return _response(VALID_LIST_METADATA_FORMATS)
        raise AssertionError(f"Unexpected URL in test: {url}")

    _mock_requests_get(monkeypatch, resolver)

    plugin = Plugin.__new__(Plugin)
    parsed = plugin.oai_metadataFormats(base)

    assert parsed["oai_dc"] == "http://www.openarchives.org/OAI/2.0/oai_dc/"


def test_get_metadata_builds_fair_eva_dataframe_shape(monkeypatch, tracking_config):
    """Exercise full metadata retrieval with mocked OAI responses.

    Mocking avoids flaky external services while checking that parsed metadata
    keeps the tabular shape consumed by FAIR EVA indicator code.
    """

    base = "https://example.org/oai"

    def resolver(url):
        if url == f"{base}?verb=ListMetadataFormats":
            return _response(VALID_LIST_METADATA_FORMATS)
        if "?verb=GetRecord" in url:
            return _response(VALID_GET_RECORD)
        raise AssertionError(f"Unexpected URL in test: {url}")

    _mock_requests_get(monkeypatch, resolver)

    plugin = Plugin(item_id="10.1234/example", api_endpoint=base, config=tracking_config, name="oai_pmh")

    assert not plugin.metadata.empty
    assert set(plugin.metadata.columns) == {
        "metadata_schema",
        "element",
        "text_value",
        "qualifier",
    }


def test_invalid_xml_does_not_pass_silently(monkeypatch):
    """Malformed XML should be surfaced as empty/fallback parsing result."""

    base = "https://example.org/oai"

    def resolver(url):
        if url == f"{base}?verb=Identify":
            return _response("<xml broken")
        raise AssertionError(f"Unexpected URL in test: {url}")

    _mock_requests_get(monkeypatch, resolver)

    plugin = Plugin.__new__(Plugin)
    xml_tree = plugin.oai_request(base, "?verb=Identify")
    assert isinstance(xml_tree, ET.Element)
    assert xml_tree.tag == "OAI-PMH"


def test_missing_expected_namespace_produces_empty_formats(monkeypatch):
    """Negative case: format entries without OAI namespace should not match."""

    base = "https://example.org/oai"
    bad_xml = """
    <OAI-PMH>
      <ListMetadataFormats>
        <metadataFormat>
          <metadataPrefix>oai_dc</metadataPrefix>
          <metadataNamespace>http://www.openarchives.org/OAI/2.0/oai_dc/</metadataNamespace>
        </metadataFormat>
      </ListMetadataFormats>
    </OAI-PMH>
    """

    def resolver(url):
        if url == f"{base}?verb=ListMetadataFormats":
            return _response(bad_xml)
        raise AssertionError(f"Unexpected URL in test: {url}")

    _mock_requests_get(monkeypatch, resolver)

    plugin = Plugin.__new__(Plugin)
    parsed = plugin.oai_metadataFormats(base)
    assert parsed == {}


def test_error_response_during_getrecord_does_not_fake_success(monkeypatch):
    """Negative case: OAI error payload should not be treated as valid URL."""

    def resolver(url):  # noqa: ARG001
        return _response(ERROR_GET_RECORD)

    _mock_requests_get(monkeypatch, resolver)

    plugin = Plugin.__new__(Plugin)
    resolved_url = plugin.oai_check_record_url(
        "https://example.org/oai", "oai_dc", "10.1234/example"
    )
    assert resolved_url == ""
