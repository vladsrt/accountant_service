"""
Bank Statement CSV parsing service.

Wraps the bank2ynab library to detect Polish bank CSV formats
(mBank, PKO BP, Bank Pekao, Alior Bank, and others) and convert them
into a standardised list of YNAB-format dicts.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
from pathlib import Path

import numpy as np
from bank2ynab.config_handler import ConfigHandler
from bank2ynab.dataframe_handler import DataframeHandler
from bank2ynab.transactionfile_reader import detect_encoding, get_files

logger = logging.getLogger(__name__)

STANDARD_COLUMNS = ["Date", "Payee", "Memo", "Outflow", "Inflow"]


class BankStatementParseError(Exception):
    """Raised when no bank2ynab configuration matches the uploaded filename."""


class BankStatementService:
    """
    Parses raw CSV bank statement exports into standardised YNAB-format dicts.

    Workflow:
      1. Write the raw bytes to a secure temporary directory.
      2. Iterate over every bank section in bank2ynab.conf; the first whose
         filename pattern matches the uploaded filename is used for parsing.
      3. Use DataframeHandler directly (no file I/O output) to produce an
         in-memory dataframe.
      4. Return the Date, Payee, Memo, Outflow, Inflow columns as a list of dicts.
      5. Guarantee deletion of the temp directory via try/finally regardless
         of whether parsing succeeds or fails.
    """

    async def parse_csv(self, file_content: bytes, filename: str) -> list[dict]:
        """Parse a raw CSV bank statement and return standardised rows.

        The bank format is auto-detected from the filename using bank2ynab's
        built-in configuration (no manual bank selection required).

        Args:
            file_content: Raw bytes of the uploaded CSV file.
            filename: Original filename — used by bank2ynab for format detection
                      via its filename-pattern rules (e.g. regex against
                      ``eKonto_*`` for mBank, ``history_csv_*`` for PKO BP).

        Returns:
            List of dicts, each with keys: ``Date``, ``Payee``, ``Memo``,
            ``Outflow``, ``Inflow``.  Dates are ISO-8601 strings (``YYYY-MM-DD``).
            Monetary values are floats.

        Raises:
            BankStatementParseError: If no configured bank format matches the
                filename, or if bank2ynab's configuration file cannot be found.
        """
        return await asyncio.to_thread(self._parse_sync, file_content, filename)

    def _parse_sync(self, file_content: bytes, filename: str) -> list[dict]:
        """Synchronous core invoked inside a thread by parse_csv."""
        safe_name = Path(filename).name
        tmp_dir = tempfile.mkdtemp(prefix="bank_stmt_")
        try:
            tmp_file = Path(tmp_dir) / safe_name
            tmp_file.write_bytes(file_content)
            return self._detect_and_parse(str(tmp_file), tmp_dir, safe_name)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _detect_and_parse(
        self,
        tmp_file_path: str,
        tmp_dir: str,
        filename: str,
    ) -> list[dict]:
        """Match the file to a bank configuration and run the parser.

        Iterates over every section in bank2ynab.conf. For each section the
        library's own get_files() is used to test whether the filename matches
        the configured pattern, keeping the detection logic identical to the
        CLI tool's behaviour.

        Args:
            tmp_file_path: Absolute path to the temp copy of the uploaded file.
            tmp_dir: Directory that contains tmp_file_path.
            filename: Safe (basename-only) version of the original filename.

        Returns:
            Standardised list of dicts (see parse_csv docstring).

        Raises:
            BankStatementParseError: If no section matches or config is missing.
        """
        try:
            config_handler = ConfigHandler()
        except FileNotFoundError as exc:
            raise BankStatementParseError("bank2ynab configuration file not found") from exc

        for section in config_handler.config.sections():
            config_dict = config_handler.fix_conf_params(section)

            matching = get_files(
                name=config_dict["bank_name"],
                file_pattern=config_dict["input_filename"],
                try_path=tmp_dir,
                regex_active=config_dict["regex"],
                ext=config_dict["ext"],
                prefix=config_dict["fixed_prefix"],
            )

            if not matching:
                continue

            logger.info("Matched bank format '%s' for file '%s'", section, filename)

            src_file = matching[0]
            encod = detect_encoding(src_file)

            df_handler = DataframeHandler()
            try:
                df_handler.run(
                    file_path=src_file,
                    delim=config_dict["input_delimiter"],
                    header_rows=int(config_dict["header_rows"]),
                    footer_rows=int(config_dict["footer_rows"]),
                    encod=encod,
                    input_columns=config_dict["input_columns"],
                    output_columns=config_dict["output_columns"],
                    api_columns=config_dict["api_columns"],
                    cd_flags=config_dict["cd_flags"],
                    date_format=config_dict["date_format"],
                    date_dedupe=config_dict["date_dedupe"],
                    fill_memo=config_dict["payee_to_memo"],
                    currency_fix=config_dict["currency_mult"],
                )
            except ValueError as exc:
                raise BankStatementParseError(
                    f"bank2ynab could not parse '{filename}' as '{section}': {exc}"
                ) from exc

            if df_handler.df.empty:
                logger.info("No transactions found in '%s' for bank '%s'", filename, section)
                return []

            available = [c for c in STANDARD_COLUMNS if c in df_handler.output_df.columns]
            return df_handler.output_df[available].replace({np.nan: None}).to_dict(orient="records")

        raise BankStatementParseError(
            f"No bank2ynab configuration matched filename: '{filename}'. "
            "Ensure the filename follows one of the supported bank export patterns "
            "(e.g. eKonto_* for mBank, history_csv_* for PKO BP)."
        )
