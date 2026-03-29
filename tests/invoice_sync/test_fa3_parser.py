"""Unit tests for FA3Parser."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from app.services.fa3_parser import FA3ParseError, FA3Parser


# ---------------------------------------------------------------------------
# TestFA3ParserBasic
# ---------------------------------------------------------------------------


class TestFA3ParserBasic:
    """Tests for FA3Parser.parse() with various XML inputs."""

    def test_parse_full_invoice_seller_nip(
        self, sample_xml_content: str
    ) -> None:
        """Seller NIP must be extracted from Podmiot1."""
        result = FA3Parser.parse(sample_xml_content)
        assert result["seller_nip"] is not None

    def test_parse_full_invoice_buyer_nip(
        self, sample_xml_content: str
    ) -> None:
        """Buyer NIP must match the value in the fixture."""
        result = FA3Parser.parse(sample_xml_content)
        assert result["buyer_nip"] == "3861610227"

    def test_parse_full_invoice_total_gross(
        self, sample_xml_content: str
    ) -> None:
        """Total gross must match the P_15 value in the fixture."""
        result = FA3Parser.parse(sample_xml_content)
        assert result["total_gross"] == "13102.43"

    def test_parse_full_invoice_p7_count(
        self, sample_xml_content: str
    ) -> None:
        """There should be exactly 6 P_7 descriptions in the fixture."""
        result = FA3Parser.parse(sample_xml_content)
        assert len(result["p7_descriptions"]) == 6

    def test_parse_full_invoice_p7_max_length(
        self, sample_xml_content: str
    ) -> None:
        """No P_7 description should exceed 512 characters."""
        result = FA3Parser.parse(sample_xml_content)
        assert all(len(desc) <= 512 for desc in result["p7_descriptions"])

    def test_parse_full_invoice_invoice_number(
        self, sample_xml_content: str
    ) -> None:
        """Invoice number must contain 'FA/'."""
        result = FA3Parser.parse(sample_xml_content)
        assert result["invoice_number"] is not None
        assert "FA/" in result["invoice_number"]

    def test_parse_full_invoice_issue_date(
        self, sample_xml_content: str
    ) -> None:
        """Issue date must not be None."""
        result = FA3Parser.parse(sample_xml_content)
        assert result["issue_date"] is not None

    def test_parse_invalid_xml(self, invalid_xml_content: str) -> None:
        """FA3ParseError should be raised for invalid XML."""
        with pytest.raises(FA3ParseError):
            FA3Parser.parse(invalid_xml_content)

    def test_parse_missing_buyer_nip(self) -> None:
        """When Podmiot2 is absent, buyer_nip should be None."""
        xml = '''\
<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="http://crd.gov.pl/wzor/2025/06/25/13775/">
  <Podmiot1>
    <DaneIdentyfikacyjne><NIP>5213000111</NIP></DaneIdentyfikacyjne>
  </Podmiot1>
  <Fa>
    <P_1>2026-01-20</P_1>
    <P_2>FV/2026/01/001</P_2>
    <P_15>100.00</P_15>
  </Fa>
</Faktura>'''
        result = FA3Parser.parse(xml)
        assert result["buyer_nip"] is None

    def test_parse_missing_buyer_nip_other_fields(self) -> None:
        """When Podmiot2 is absent, other fields must still parse correctly."""
        xml = '''\
<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="http://crd.gov.pl/wzor/2025/06/25/13775/">
  <Podmiot1>
    <DaneIdentyfikacyjne><NIP>5213000111</NIP></DaneIdentyfikacyjne>
  </Podmiot1>
  <Fa>
    <P_1>2026-01-20</P_1>
    <P_2>FV/2026/01/001</P_2>
    <P_15>100.00</P_15>
  </Fa>
</Faktura>'''
        result = FA3Parser.parse(xml)
        assert result["seller_nip"] == "5213000111"
        assert result["total_gross"] == "100.00"

    def test_parse_empty_fa_wiersz(self) -> None:
        """When no FaWiersz elements exist, p7_descriptions should be []."""
        xml = '''\
<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="http://crd.gov.pl/wzor/2025/06/25/13775/">
  <Podmiot1>
    <DaneIdentyfikacyjne><NIP>5213000111</NIP></DaneIdentyfikacyjne>
  </Podmiot1>
  <Fa>
    <P_1>2026-03-01</P_1>
    <P_2>FV/2026/03/001</P_2>
    <P_15>500.00</P_15>
  </Fa>
</Faktura>'''
        result = FA3Parser.parse(xml)
        assert result["p7_descriptions"] == []

    def test_parse_p7_truncation(self) -> None:
        """P_7 values longer than 512 characters must be truncated to 512."""
        long_text = "A" * 1000
        xml = f'''\
<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="http://crd.gov.pl/wzor/2025/06/25/13775/">
  <Fa>
    <P_1>2026-01-01</P_1>
    <P_2>FV/TRUNC/001</P_2>
    <P_15>1.00</P_15>
    <FaWiersz><P_7>{long_text}</P_7></FaWiersz>
  </Fa>
</Faktura>'''
        result = FA3Parser.parse(xml)
        assert len(result["p7_descriptions"][0]) == 512

    def test_parse_multiple_p7(self) -> None:
        """Multiple FaWiersz elements should produce multiple p7 entries."""
        xml = '''\
<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="http://crd.gov.pl/wzor/2025/06/25/13775/">
  <Fa>
    <P_1>2026-01-01</P_1>
    <P_2>FV/MULTI/001</P_2>
    <P_15>300.00</P_15>
    <FaWiersz><P_7>Pozycja pierwsza</P_7></FaWiersz>
    <FaWiersz><P_7>Pozycja druga</P_7></FaWiersz>
    <FaWiersz><P_7>Pozycja trzecia</P_7></FaWiersz>
  </Fa>
</Faktura>'''
        result = FA3Parser.parse(xml)
        assert len(result["p7_descriptions"]) == 3


# ---------------------------------------------------------------------------
# TestFA3ParserNamespace
# ---------------------------------------------------------------------------


class TestFA3ParserNamespace:
    """Tests for namespace detection logic."""

    def test_detect_namespace_fa3(self) -> None:
        """FA(3) XML should produce the correct namespace URI."""
        xml = '''\
<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="http://crd.gov.pl/wzor/2025/06/25/13775/">
  <Fa><P_1>2026-01-01</P_1></Fa>
</Faktura>'''
        root = ET.fromstring(xml)
        ns = FA3Parser._detect_namespace(root)
        assert ns == "http://crd.gov.pl/wzor/2025/06/25/13775/"

    def test_detect_namespace_empty(self) -> None:
        """XML without a namespace should return an empty string."""
        xml = '<Faktura><Fa><P_1>2026-01-01</P_1></Fa></Faktura>'
        root = ET.fromstring(xml)
        ns = FA3Parser._detect_namespace(root)
        assert ns == ""
