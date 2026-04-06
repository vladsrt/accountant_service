"""
FA(3) XML Invoice Parser for KSeF 2.0.

Extracts structured data from FA(3) schema invoices
(namespace: http://crd.gov.pl/wzor/2025/06/25/13775/).

Uses lxml with secure parser settings to prevent XXE injection.
"""

from __future__ import annotations

import logging

from lxml import etree

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Secure XML parser — prevents XXE and SSRF attacks
# ---------------------------------------------------------------------------

_SECURE_PARSER = etree.XMLParser(resolve_entities=False, no_network=True)

# ---------------------------------------------------------------------------
# FA(3) namespace constants
# ---------------------------------------------------------------------------

# Primary FA(3) namespace (official schema effective 2026-02-01)
_NS_FA3 = "http://crd.gov.pl/wzor/2025/06/25/13775/"

# Older FA(2) namespace kept as fallback for historical invoices
_NS_FA2 = "http://crd.gov.pl/wzor/2023/06/29/12648/"

# Common namespace prefixes used in XPath queries
_NAMESPACES: dict[str, str] = {
    "fa3": _NS_FA3,
    "fa2": _NS_FA2,
}

# Maximum length for P_7 description strings
_P7_MAX_LENGTH = 512


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class FA3ParseError(Exception):
    """Raised when the XML content cannot be parsed as a valid FA(3) invoice."""


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class FA3Parser:
    """Static parser for KSeF FA(3) invoice XML documents."""

    @staticmethod
    def parse(xml_content: str) -> dict:
        """Parse an FA(3) XML invoice and extract key fields.

        Args:
            xml_content: Raw XML string of the invoice.

        Returns:
            Dictionary with extracted invoice data. Missing fields are ``None``
            (except ``p7_descriptions`` which defaults to an empty list).

        Raises:
            FA3ParseError: If the XML is fundamentally unparsable.
        """
        try:
            root = etree.fromstring(xml_content.encode("utf-8"), parser=_SECURE_PARSER)
        except etree.XMLSyntaxError as exc:
            raise FA3ParseError(f"Invalid XML: {exc}") from exc

        # Detect the active namespace from the root tag
        ns = FA3Parser._detect_namespace(root)
        ns_map = {"ns": ns} if ns else {}

        return {
            "ksef_reference_number": FA3Parser._extract_ksef_reference(root, ns_map),
            "invoice_number": FA3Parser._find_text(root, ".//ns:P_2", ns_map),
            "issue_date": FA3Parser._find_text(root, ".//ns:P_1", ns_map),
            "seller_nip": FA3Parser._extract_nip(root, "Podmiot1", ns_map),
            "buyer_nip": FA3Parser._extract_nip(root, "Podmiot2", ns_map),
            "total_gross": FA3Parser._extract_total_gross(root, ns_map),
            "p7_descriptions": FA3Parser._extract_p7_descriptions(root, ns_map),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_namespace(root: etree._Element) -> str:
        """Extract the namespace URI from the root element's tag."""
        tag = root.tag if isinstance(root.tag, str) else ""
        if tag.startswith("{"):
            return tag.split("}")[0].lstrip("{")
        return ""

    @staticmethod
    def _find_text(
        root: etree._Element,
        xpath: str,
        ns_map: dict[str, str],
    ) -> str | None:
        """Find an element by XPath and return its text, or ``None``."""
        # If no namespace, try plain xpath (strip 'ns:' prefix)
        if not ns_map:
            plain_xpath = xpath.replace("ns:", "")
            elem = root.find(plain_xpath)
        else:
            elem = root.find(xpath, ns_map)
        if elem is not None and elem.text:
            return elem.text.strip()
        return None

    @staticmethod
    def _extract_ksef_reference(
        root: etree._Element,
        ns_map: dict[str, str],
    ) -> str | None:
        """Try multiple locations for the KSeF reference number.

        Priority:
        1. <NumerKSeF> element (KSeF wrapper)
        2. Root attribute ``KsefReferenceNumber``
        3. <Naglowek>/<NumerFaktury> or <P_2> as last resort
        """
        # 1. <NumerKSeF> anywhere in the document (any namespace)
        for elem in root.iter():
            tag = elem.tag if isinstance(elem.tag, str) else ""
            local = tag.split("}")[-1] if "}" in tag else tag
            if local == "NumerKSeF" and elem.text:
                return elem.text.strip()

        # 2. Root-level attributes
        for attr_name in ("KsefReferenceNumber", "ksefReferenceNumber"):
            val = root.get(attr_name)
            if val:
                return val.strip()

        # 3. Fallback to <NumerFaktury>
        for elem in root.iter():
            tag = elem.tag if isinstance(elem.tag, str) else ""
            local = tag.split("}")[-1] if "}" in tag else tag
            if local == "NumerFaktury" and elem.text:
                return elem.text.strip()

        return None

    @staticmethod
    def _extract_nip(
        root: etree._Element,
        podmiot_tag: str,
        ns_map: dict[str, str],
    ) -> str | None:
        """Extract NIP from Podmiot1 or Podmiot2 → DaneIdentyfikacyjne → NIP."""
        # Search with namespace
        xpath = f".//ns:{podmiot_tag}/ns:DaneIdentyfikacyjne/ns:NIP"
        result = FA3Parser._find_text(root, xpath, ns_map)
        if result:
            return result.replace("-", "").replace(" ", "")

        # Fallback: namespace-agnostic iteration
        for podmiot in root.iter():
            tag = podmiot.tag if isinstance(podmiot.tag, str) else ""
            local = tag.split("}")[-1] if "}" in tag else tag
            if local == podmiot_tag:
                for dane in podmiot.iter():
                    dane_tag = dane.tag if isinstance(dane.tag, str) else ""
                    dane_local = dane_tag.split("}")[-1] if "}" in dane_tag else dane_tag
                    if dane_local == "DaneIdentyfikacyjne":
                        for nip_el in dane.iter():
                            nip_tag = nip_el.tag if isinstance(nip_el.tag, str) else ""
                            nip_local = (
                                nip_tag.split("}")[-1] if "}" in nip_tag else nip_tag
                            )
                            if nip_local == "NIP" and nip_el.text:
                                return nip_el.text.strip().replace("-", "").replace(" ", "")
        return None

    @staticmethod
    def _extract_total_gross(
        root: etree._Element,
        ns_map: dict[str, str],
    ) -> str | None:
        """Extract the total gross amount (P_15, first occurrence)."""
        result = FA3Parser._find_text(root, ".//ns:P_15", ns_map)
        if result:
            return result

        # Namespace-agnostic fallback
        for elem in root.iter():
            tag = elem.tag if isinstance(elem.tag, str) else ""
            local = tag.split("}")[-1] if "}" in tag else tag
            if local == "P_15" and elem.text:
                return elem.text.strip()
        return None

    @staticmethod
    def _extract_p7_descriptions(
        root: etree._Element,
        ns_map: dict[str, str],
    ) -> list[str]:
        """Collect all FaWiersz/P_7 text values, capped at 512 chars each."""
        descriptions: list[str] = []

        # Try namespace-aware first
        if ns_map:
            for wiersz in root.findall(".//ns:FaWiersz", ns_map):
                p7 = wiersz.find("ns:P_7", ns_map)
                if p7 is not None and p7.text:
                    descriptions.append(p7.text.strip()[:_P7_MAX_LENGTH])

        # Fallback: namespace-agnostic
        if not descriptions:
            for elem in root.iter():
                tag = elem.tag if isinstance(elem.tag, str) else ""
                local = tag.split("}")[-1] if "}" in tag else tag
                if local == "FaWiersz":
                    for child in elem:
                        child_tag = child.tag if isinstance(child.tag, str) else ""
                        child_local = child_tag.split("}")[-1] if "}" in child_tag else child_tag
                        if child_local == "P_7" and child.text:
                            descriptions.append(child.text.strip()[:_P7_MAX_LENGTH])

        return descriptions
