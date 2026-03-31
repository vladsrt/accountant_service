"""
Unit tests for BankStatementService.

Strategy:
- The bank2ynab boundary is mocked at the _detect_and_parse level for
  lifecycle and async tests (so we own the temp-dir logic but swap out
  the library-specific detection/parsing).
- Separate tests go one level deeper — mocking only get_files and
  DataframeHandler — to verify the detection and column-selection logic.
- A dedicated test verifies BankStatementParseError is raised when no
  bank format matches the filename.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from app.services.bank_statement_service import (
    STANDARD_COLUMNS,
    BankStatementParseError,
    BankStatementService,
)

MBANK_FILENAME = "eKonto_12345678_230801_230916.csv"

MBANK_CSV_BYTES = (
    b"#Data operacji\t#Data ksi\xc4\x99gowania\t#Opis operacji\t"
    b"#Tytu\xc5\x82\t#Nadawca/Odbiorca\t#Numer konta\t#Kwota\t#Saldo po operacji\n"
    b"2023-08-01\t2023-08-01\tPrzelew wychodz\xc4\x85cy\t\tZUS\t12345678\t-1500,00\t5000,00\n"
    b"2023-08-02\t2023-08-02\tZap\xc5\x82ata\t\tAllegrosy\t87654321\t200,00\t5200,00\n"
)

PARSED_ROWS = [
    {"Date": "2023-08-01", "Payee": "Zus", "Memo": "Zus", "Outflow": 1500.0, "Inflow": 0.0},
    {"Date": "2023-08-02", "Payee": "Allegrosy", "Memo": "Allegrosy", "Outflow": 0.0, "Inflow": 200.0},
]


@pytest.fixture
def service() -> BankStatementService:
    return BankStatementService()


# ---------------------------------------------------------------------------
# Async interface
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parse_csv_async_delegates_to_sync(service: BankStatementService) -> None:
    """parse_csv() should call _parse_sync inside a thread and return its result."""
    with patch.object(service, "_parse_sync", return_value=PARSED_ROWS) as mock_sync:
        result = await service.parse_csv(MBANK_CSV_BYTES, MBANK_FILENAME)

    assert result == PARSED_ROWS
    mock_sync.assert_called_once_with(MBANK_CSV_BYTES, MBANK_FILENAME)


# ---------------------------------------------------------------------------
# Temp-file lifecycle
# ---------------------------------------------------------------------------


def test_temp_dir_is_deleted_after_successful_parse(service: BankStatementService) -> None:
    """The temp directory must not exist after a successful parse."""
    captured: list[str] = []

    def record_tmp_dir(tmp_file_path: str, tmp_dir: str, filename: str) -> list[dict]:
        captured.append(tmp_dir)
        assert Path(tmp_dir).is_dir(), "tmp_dir should exist while _detect_and_parse runs"
        assert (Path(tmp_dir) / filename).is_file(), "temp file should exist inside tmp_dir"
        return PARSED_ROWS

    with patch.object(service, "_detect_and_parse", side_effect=record_tmp_dir):
        service._parse_sync(MBANK_CSV_BYTES, MBANK_FILENAME)

    assert len(captured) == 1
    assert not Path(captured[0]).exists(), "tmp_dir should be removed after _parse_sync"


def test_temp_dir_is_deleted_after_failed_parse(service: BankStatementService) -> None:
    """The temp directory must not exist even when _detect_and_parse raises."""
    captured: list[str] = []

    def record_and_raise(tmp_file_path: str, tmp_dir: str, filename: str) -> list[dict]:
        captured.append(tmp_dir)
        raise BankStatementParseError("no bank matched")

    with patch.object(service, "_detect_and_parse", side_effect=record_and_raise):
        with pytest.raises(BankStatementParseError):
            service._parse_sync(MBANK_CSV_BYTES, MBANK_FILENAME)

    assert not Path(captured[0]).exists(), "tmp_dir should be removed even on parse failure"


def test_path_traversal_in_filename_is_neutralised(service: BankStatementService) -> None:
    """A filename with path components must not escape the temp directory."""
    captured: list[str] = []

    def record_tmp_dir(tmp_file_path: str, tmp_dir: str, filename: str) -> list[dict]:
        captured.append(tmp_file_path)
        return []

    with patch.object(service, "_detect_and_parse", side_effect=record_tmp_dir):
        service._parse_sync(b"data", "../../etc/passwd")

    # The resolved path must still be inside tmp_dir
    resolved = Path(captured[0]).resolve()
    assert resolved.name == "passwd"
    # The parent must be the temp dir, not /etc
    assert str(resolved.parent) != "/etc"


# ---------------------------------------------------------------------------
# Detection + column-selection logic
# ---------------------------------------------------------------------------


def _make_output_df() -> pd.DataFrame:
    """Return a minimal DataFrame that matches the standard output columns."""
    return pd.DataFrame(
        {
            "Date": ["2023-08-01", "2023-08-02"],
            "Payee": ["Zus", "Allegrosy"],
            "Category": ["", ""],
            "Memo": ["Zus", "Allegrosy"],
            "Outflow": [1500.0, 0.0],
            "Inflow": [0.0, 200.0],
        }
    )


def test_detect_and_parse_returns_standard_columns(service: BankStatementService, tmp_path: Path) -> None:
    """_detect_and_parse should select only the five STANDARD_COLUMNS from output_df."""
    test_file = tmp_path / MBANK_FILENAME
    test_file.write_bytes(MBANK_CSV_BYTES)

    mock_config = MagicMock()
    mock_config.config.sections.return_value = ["PL mBank"]
    mock_config.fix_conf_params.return_value = {
        "bank_name": "PL mBank",
        "input_filename": "eKonto_",
        "path": str(tmp_path),
        "regex": False,
        "ext": ".csv",
        "fixed_prefix": "fixed_",
        "input_delimiter": "\t",
        "header_rows": 1,
        "footer_rows": 0,
        "input_columns": ["Date", "skip", "Memo", "skip", "Payee", "skip", "Inflow", "skip"],
        "output_columns": ["Date", "Payee", "Category", "Memo", "Outflow", "Inflow"],
        "api_columns": ["account_id", "date", "payee_name", "amount", "memo", "category", "cleared", "import_id"],
        "cd_flags": [""],
        "date_format": "",
        "date_dedupe": False,
        "payee_to_memo": True,
        "currency_mult": 1.0,
        "save_output": False,
        "delete_original": False,
        "plugin": "",
        "plugin_args": [""],
        "api_token": "",
        "api_account": [""],
        "encoding": "",
    }

    output_df = _make_output_df()
    mock_df_handler = MagicMock()
    mock_df_handler.df.empty = False
    mock_df_handler.output_df = output_df

    with (
        patch("app.services.bank_statement_service.ConfigHandler", return_value=mock_config),
        patch("app.services.bank_statement_service.get_files", return_value=[str(test_file)]),
        patch("app.services.bank_statement_service.detect_encoding", return_value="utf-8"),
        patch("app.services.bank_statement_service.DataframeHandler", return_value=mock_df_handler),
    ):
        result = service._detect_and_parse(str(test_file), str(tmp_path), MBANK_FILENAME)

    assert isinstance(result, list)
    assert len(result) == 2
    for row in result:
        assert set(row.keys()) == set(STANDARD_COLUMNS)
    assert result[0]["Date"] == "2023-08-01"
    assert result[0]["Outflow"] == 1500.0
    assert result[1]["Inflow"] == 200.0


def test_detect_and_parse_returns_empty_list_when_df_is_empty(
    service: BankStatementService, tmp_path: Path
) -> None:
    """An empty dataframe (no valid transactions) should yield an empty list, not an error."""
    test_file = tmp_path / MBANK_FILENAME
    test_file.write_bytes(MBANK_CSV_BYTES)

    mock_config = MagicMock()
    mock_config.config.sections.return_value = ["PL mBank"]
    mock_config.fix_conf_params.return_value = {
        "bank_name": "PL mBank",
        "input_filename": "eKonto_",
        "path": str(tmp_path),
        "regex": False,
        "ext": ".csv",
        "fixed_prefix": "fixed_",
        "input_delimiter": "\t",
        "header_rows": 1,
        "footer_rows": 0,
        "input_columns": ["Date", "Inflow"],
        "output_columns": ["Date", "Payee", "Category", "Memo", "Outflow", "Inflow"],
        "api_columns": ["account_id", "date", "payee_name", "amount", "memo", "category", "cleared", "import_id"],
        "cd_flags": [""],
        "date_format": "",
        "date_dedupe": False,
        "payee_to_memo": False,
        "currency_mult": 1.0,
        "save_output": False,
        "delete_original": False,
        "plugin": "",
        "plugin_args": [""],
        "api_token": "",
        "api_account": [""],
        "encoding": "",
    }

    mock_df_handler = MagicMock()
    mock_df_handler.df.empty = True

    with (
        patch("app.services.bank_statement_service.ConfigHandler", return_value=mock_config),
        patch("app.services.bank_statement_service.get_files", return_value=[str(test_file)]),
        patch("app.services.bank_statement_service.detect_encoding", return_value="utf-8"),
        patch("app.services.bank_statement_service.DataframeHandler", return_value=mock_df_handler),
    ):
        result = service._detect_and_parse(str(test_file), str(tmp_path), MBANK_FILENAME)

    assert result == []


def test_detect_and_parse_raises_when_no_bank_matches(
    service: BankStatementService, tmp_path: Path
) -> None:
    """BankStatementParseError must be raised when no section's pattern matches the filename."""
    unrecognized_file = tmp_path / "unknown_export_20230901.xyz"
    unrecognized_file.write_bytes(b"col1,col2\nval1,val2\n")

    mock_config = MagicMock()
    mock_config.config.sections.return_value = ["PL mBank", "PL PKO BP"]
    mock_config.fix_conf_params.side_effect = lambda section: {
        "bank_name": section,
        "input_filename": "nomatch",
        "path": str(tmp_path),
        "regex": False,
        "ext": ".csv",
        "fixed_prefix": "fixed_",
    }

    with (
        patch("app.services.bank_statement_service.ConfigHandler", return_value=mock_config),
        patch("app.services.bank_statement_service.get_files", return_value=[]),
    ):
        with pytest.raises(BankStatementParseError, match="No bank2ynab configuration matched"):
            service._detect_and_parse(
                str(unrecognized_file), str(tmp_path), unrecognized_file.name
            )


def test_detect_and_parse_raises_when_config_missing(
    service: BankStatementService, tmp_path: Path
) -> None:
    """BankStatementParseError must wrap FileNotFoundError from ConfigHandler."""
    with patch(
        "app.services.bank_statement_service.ConfigHandler",
        side_effect=FileNotFoundError("config not found"),
    ):
        with pytest.raises(BankStatementParseError, match="configuration file not found"):
            service._detect_and_parse("", str(tmp_path), MBANK_FILENAME)


def test_detect_and_parse_raises_parse_error_on_value_error(
    service: BankStatementService, tmp_path: Path
) -> None:
    """A ValueError from DataframeHandler.run() must raise BankStatementParseError, not return []."""
    test_file = tmp_path / MBANK_FILENAME
    test_file.write_bytes(MBANK_CSV_BYTES)

    mock_config = MagicMock()
    mock_config.config.sections.return_value = ["PL mBank"]
    mock_config.fix_conf_params.return_value = {
        "bank_name": "PL mBank",
        "input_filename": "eKonto_",
        "path": str(tmp_path),
        "regex": False,
        "ext": ".csv",
        "fixed_prefix": "fixed_",
        "input_delimiter": "\t",
        "header_rows": 1,
        "footer_rows": 0,
        "input_columns": ["Date", "Inflow"],
        "output_columns": ["Date", "Payee", "Category", "Memo", "Outflow", "Inflow"],
        "api_columns": ["account_id", "date", "payee_name", "amount", "memo", "category", "cleared", "import_id"],
        "cd_flags": [""],
        "date_format": "",
        "date_dedupe": False,
        "payee_to_memo": False,
        "currency_mult": 1.0,
        "save_output": False,
        "delete_original": False,
        "plugin": "",
        "plugin_args": [""],
        "api_token": "",
        "api_account": [""],
        "encoding": "",
    }

    mock_df_handler = MagicMock()
    mock_df_handler.run.side_effect = ValueError("column mismatch")

    with (
        patch("app.services.bank_statement_service.ConfigHandler", return_value=mock_config),
        patch("app.services.bank_statement_service.get_files", return_value=[str(test_file)]),
        patch("app.services.bank_statement_service.detect_encoding", return_value="utf-8"),
        patch("app.services.bank_statement_service.DataframeHandler", return_value=mock_df_handler),
    ):
        with pytest.raises(BankStatementParseError, match="column mismatch"):
            service._detect_and_parse(str(test_file), str(tmp_path), MBANK_FILENAME)


def test_detect_and_parse_converts_nan_to_none(
    service: BankStatementService, tmp_path: Path
) -> None:
    """NaN values in output_df columns must be converted to None (JSON-serialisable)."""
    test_file = tmp_path / MBANK_FILENAME
    test_file.write_bytes(MBANK_CSV_BYTES)

    mock_config = MagicMock()
    mock_config.config.sections.return_value = ["PL mBank"]
    mock_config.fix_conf_params.return_value = {
        "bank_name": "PL mBank",
        "input_filename": "eKonto_",
        "path": str(tmp_path),
        "regex": False,
        "ext": ".csv",
        "fixed_prefix": "fixed_",
        "input_delimiter": "\t",
        "header_rows": 1,
        "footer_rows": 0,
        "input_columns": ["Date", "skip", "Memo", "skip", "Payee", "skip", "Inflow", "skip"],
        "output_columns": ["Date", "Payee", "Category", "Memo", "Outflow", "Inflow"],
        "api_columns": ["account_id", "date", "payee_name", "amount", "memo", "category", "cleared", "import_id"],
        "cd_flags": [""],
        "date_format": "",
        "date_dedupe": False,
        "payee_to_memo": False,
        "currency_mult": 1.0,
        "save_output": False,
        "delete_original": False,
        "plugin": "",
        "plugin_args": [""],
        "api_token": "",
        "api_account": [""],
        "encoding": "",
    }

    output_df = pd.DataFrame(
        {
            "Date": ["2023-08-01", "2023-08-02"],
            "Payee": ["Zus", np.nan],
            "Memo": [np.nan, "Allegrosy"],
            "Outflow": [1500.0, 0.0],
            "Inflow": [0.0, 200.0],
        }
    )

    mock_df_handler = MagicMock()
    mock_df_handler.df.empty = False
    mock_df_handler.output_df = output_df

    with (
        patch("app.services.bank_statement_service.ConfigHandler", return_value=mock_config),
        patch("app.services.bank_statement_service.get_files", return_value=[str(test_file)]),
        patch("app.services.bank_statement_service.detect_encoding", return_value="utf-8"),
        patch("app.services.bank_statement_service.DataframeHandler", return_value=mock_df_handler),
    ):
        result = service._detect_and_parse(str(test_file), str(tmp_path), MBANK_FILENAME)

    assert result[0]["Memo"] is None
    assert result[1]["Payee"] is None
    for row in result:
        for value in row.values():
            assert not (isinstance(value, float) and np.isnan(value)), f"NaN found in row: {row}"
