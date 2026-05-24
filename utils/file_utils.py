"""
File I/O utilities for JSON, JSONL, Pickle, Text, and CSV files.
Provides safe read/write with error handling.
"""

import json
import pickle
import csv
from pathlib import Path
from typing import Any, List, Dict, Union, Iterator, Optional
import logging

logger = logging.getLogger(__name__)


# ---------- Text (TXT) ----------
def read_text(file_path: Union[str, Path], encoding: str = "utf-8") -> str:
    """Read entire content of a text file."""
    path = Path(file_path)
    try:
        with open(path, "r", encoding=encoding) as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read text file {path}: {e}")
        raise


def write_text(file_path: Union[str, Path], content: str, encoding: str = "utf-8") -> None:
    """Write string content to a text file."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding=encoding) as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Failed to write text file {path}: {e}")
        raise


# ---------- JSON ----------
def read_json(file_path: Union[str, Path]) -> Any:
    """Load JSON from file."""
    path = Path(file_path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read JSON file {path}: {e}")
        raise


def write_json(file_path: Union[str, Path], data: Any, indent: int = 2) -> None:
    """Write data to JSON file."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to write JSON file {path}: {e}")
        raise


# ---------- JSONL (JSON Lines) ----------
def read_jsonl(file_path: Union[str, Path]) -> List[Dict]:
    """Read JSONL file (one JSON object per line) into a list of dicts."""
    path = Path(file_path)
    data = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data.append(json.loads(line))
        return data
    except Exception as e:
        logger.error(f"Failed to read JSONL file {path}: {e}")
        raise


def write_jsonl(file_path: Union[str, Path], data: List[Dict]) -> None:
    """Write list of dicts to JSONL file."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Failed to write JSONL file {path}: {e}")
        raise


def stream_jsonl(file_path: Union[str, Path]) -> Iterator[Dict]:
    """
    Stream JSONL file line by line, yielding one dict at a time.
    Useful for large files that don't fit in memory.
    """
    path = Path(file_path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)
    except Exception as e:
        logger.error(f"Failed to stream JSONL file {path}: {e}")
        raise


# ---------- Pickle ----------
def read_pickle(file_path: Union[str, Path]) -> Any:
    """Load Python object from pickle file."""
    path = Path(file_path)
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        logger.error(f"Failed to read pickle file {path}: {e}")
        raise


def write_pickle(file_path: Union[str, Path], data: Any, protocol: int = pickle.HIGHEST_PROTOCOL) -> None:
    """Write Python object to pickle file."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "wb") as f:
            pickle.dump(data, f, protocol=protocol)
    except Exception as e:
        logger.error(f"Failed to write pickle file {path}: {e}")
        raise


# ---------- CSV ----------
def read_csv(
    file_path: Union[str, Path],
    delimiter: str = ",",
    has_header: bool = True,
    encoding: str = "utf-8"
) -> Union[List[Dict], List[List[str]]]:
    """
    Read CSV file.
    If has_header=True, returns list of dictionaries (fieldnames as keys).
    Else, returns list of rows (each row is list of strings).
    """
    path = Path(file_path)
    try:
        with open(path, "r", encoding=encoding) as f:
            reader = csv.reader(f, delimiter=delimiter)
            if has_header:
                header = next(reader)
                data = []
                for row in reader:
                    data.append({header[i]: row[i] for i in range(len(header))})
                return data
            else:
                return list(reader)
    except Exception as e:
        logger.error(f"Failed to read CSV file {path}: {e}")
        raise


def write_csv(
    file_path: Union[str, Path],
    data: Union[List[Dict], List[List[str]]],
    delimiter: str = ",",
    fieldnames: Optional[List[str]] = None,
    encoding: str = "utf-8"
) -> None:
    """
    Write CSV file.
    If data is list of dicts, fieldnames can be provided or inferred (keys of first dict).
    If data is list of lists, writes as rows without header.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding=encoding, newline="") as f:
            if data and isinstance(data[0], dict):
                # Write dict as CSV with header
                if fieldnames is None:
                    fieldnames = list(data[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
                writer.writeheader()
                writer.writerows(data)
            else:
                # Write list of lists
                writer = csv.writer(f, delimiter=delimiter)
                writer.writerows(data)
    except Exception as e:
        logger.error(f"Failed to write CSV file {path}: {e}")
        raise


# ---------- Generic safe read/write ----------
def safe_read_json(file_path: Union[str, Path], default: Any = None) -> Any:
    """Try to read JSON, return default if file not found or error."""
    try:
        return read_json(file_path)
    except FileNotFoundError:
        return default
    except Exception:
        return default


def safe_write_json(file_path: Union[str, Path], data: Any, indent: int = 2) -> bool:
    """Try to write JSON, return True if success else False."""
    try:
        write_json(file_path, data, indent)
        return True
    except Exception:
        return False