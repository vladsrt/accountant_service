"""Shared fixtures for invoice_sync tests."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from app.core.config import Settings


# ---------------------------------------------------------------------------
# FA(3) XML fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_xml_content() -> str:
    """Realistic FA(3) invoice XML with all fields populated.

    Mirrors a real KSeF FA(3) document with 6 line items,
    Podmiot1 (seller) and Podmiot2 (buyer), totals, and header.
    """
    return '''\
<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="http://crd.gov.pl/wzor/2025/06/25/13775/"
         xmlns:etd="http://crd.gov.pl/xml/schematy/dziedzinowe/mf/2022/01/05/eD/DefinicjeTypy/"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Naglowek>
    <KodFormularza kodSystemowy="FA (3)" wersjaSchemy="1-0E">FA</KodFormularza>
    <WariantFormularza>3</WariantFormularza>
    <DataWytworzeniaFa>2026-01-20T14:30:00</DataWytworzeniaFa>
    <SystemInfo>KSeF</SystemInfo>
    <NumerKSeF>1234567890-20260120-AABBCC-DD</NumerKSeF>
  </Naglowek>
  <Podmiot1>
    <DaneIdentyfikacyjne>
      <NIP>5213000111</NIP>
      <Nazwa>Firma Sprzedawca Sp. z o.o.</Nazwa>
    </DaneIdentyfikacyjne>
    <Adres>
      <KodKraju>PL</KodKraju>
      <AdresL1>ul. Testowa 1</AdresL1>
      <AdresL2>00-001 Warszawa</AdresL2>
    </Adres>
  </Podmiot1>
  <Podmiot2>
    <DaneIdentyfikacyjne>
      <NIP>3861610227</NIP>
      <Nazwa>Klient Nabywca S.A.</Nazwa>
    </DaneIdentyfikacyjne>
    <Adres>
      <KodKraju>PL</KodKraju>
      <AdresL1>ul. Kupiecka 42</AdresL1>
      <AdresL2>30-300 Kraków</AdresL2>
    </Adres>
  </Podmiot2>
  <Fa>
    <KodWaluty>PLN</KodWaluty>
    <P_1>2026-01-20</P_1>
    <P_2>FA/2026/01/00042</P_2>
    <P_13_1>10652.38</P_13_1>
    <P_14_1>2450.05</P_14_1>
    <P_15>13102.43</P_15>
    <Adnotacje>
      <P_16>2</P_16>
      <P_17>2</P_17>
      <P_18>2</P_18>
      <P_18A>2</P_18A>
      <Zwolnienie><P_19N>1</P_19N></Zwolnienie>
      <NoweSrodkiTransportu><P_22N>1</P_22N></NoweSrodkiTransportu>
      <P_23>2</P_23>
      <PMarzy><P_PMarzyN>1</P_PMarzyN></PMarzy>
    </Adnotacje>
    <FaWiersz>
      <NrWierszaFa>1</NrWierszaFa>
      <P_7>Usługi księgowe - prowadzenie KPiR za styczeń 2026</P_7>
      <P_8A>szt.</P_8A>
      <P_8B>1</P_8B>
      <P_9A>3500.00</P_9A>
      <P_11>3500.00</P_11>
      <P_12>23</P_12>
    </FaWiersz>
    <FaWiersz>
      <NrWierszaFa>2</NrWierszaFa>
      <P_7>Sporządzenie deklaracji VAT-7 za grudzień 2025</P_7>
      <P_8A>szt.</P_8A>
      <P_8B>1</P_8B>
      <P_9A>1200.00</P_9A>
      <P_11>1200.00</P_11>
      <P_12>23</P_12>
    </FaWiersz>
    <FaWiersz>
      <NrWierszaFa>3</NrWierszaFa>
      <P_7>Obsługa kadrowo-płacowa (5 pracowników) - styczeń 2026</P_7>
      <P_8A>szt.</P_8A>
      <P_8B>5</P_8B>
      <P_9A>450.00</P_9A>
      <P_11>2250.00</P_11>
      <P_12>23</P_12>
    </FaWiersz>
    <FaWiersz>
      <NrWierszaFa>4</NrWierszaFa>
      <P_7>Analiza i optymalizacja kosztów podatkowych Q4 2025</P_7>
      <P_8A>szt.</P_8A>
      <P_8B>1</P_8B>
      <P_9A>2500.00</P_9A>
      <P_11>2500.00</P_11>
      <P_12>23</P_12>
    </FaWiersz>
    <FaWiersz>
      <NrWierszaFa>5</NrWierszaFa>
      <P_7>Przygotowanie rocznego zeznania CIT-8 za 2025</P_7>
      <P_8A>szt.</P_8A>
      <P_8B>1</P_8B>
      <P_9A>902.38</P_9A>
      <P_11>902.38</P_11>
      <P_12>23</P_12>
    </FaWiersz>
    <FaWiersz>
      <NrWierszaFa>6</NrWierszaFa>
      <P_7>Konsultacja podatkowa - restrukturyzacja spółki</P_7>
      <P_8A>godz.</P_8A>
      <P_8B>2</P_8B>
      <P_9A>250.00</P_9A>
      <P_11>500.00</P_11>
      <P_12>23</P_12>
    </FaWiersz>
  </Fa>
</Faktura>'''


@pytest.fixture()
def minimal_xml_content() -> str:
    """Minimal valid FA(3) XML with only mandatory fields."""
    return '''\
<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="http://crd.gov.pl/wzor/2025/06/25/13775/">
  <Naglowek>
    <KodFormularza kodSystemowy="FA (3)" wersjaSchemy="1-0E">FA</KodFormularza>
    <WariantFormularza>3</WariantFormularza>
    <DataWytworzeniaFa>2026-02-01T00:00:00</DataWytworzeniaFa>
  </Naglowek>
  <Podmiot1>
    <DaneIdentyfikacyjne>
      <NIP>1111111111</NIP>
    </DaneIdentyfikacyjne>
  </Podmiot1>
  <Fa>
    <KodWaluty>PLN</KodWaluty>
    <P_1>2026-02-01</P_1>
    <P_2>FV/MIN/001</P_2>
    <P_15>100.00</P_15>
  </Fa>
</Faktura>'''


@pytest.fixture()
def invalid_xml_content() -> str:
    """Invalid XML that cannot be parsed."""
    return '<Faktura><незакрытый тег'


@pytest.fixture()
def mock_settings() -> Settings:
    """Settings configured for unit tests (no real API calls)."""
    master_key = Fernet.generate_key().decode()
    return Settings(
        KSEF_SYNC_DATE_FROM="2026-01-01",
        KSEF_BASE_URL="https://api-test.ksef.mf.gov.pl",
        ENCRYPTION_MASTER_KEY=master_key,
        KSEF_EXPORT_POLL_INTERVAL=0.1,
        KSEF_EXPORT_TIMEOUT=5.0,
        KSEF_DOWNLOAD_DIR="/tmp/ksef_test_exports",
        KSEF_TOKEN="test-token",
        KSEF_NIP="0000000000",
        DB_HOST="localhost",
        DB_PORT=5432,
        DB_USER="test",
        DB_PASS="test",
        DB_NAME="test_db",
    )
