import csv
import io


def sanitize_csv_cell(value: str) -> str:
    """
    Prevent spreadsheet formula injection by prefixing a single quote when a cell
    starts with =, +, -, @ (after trimming left whitespace).
    """
    if value is None:
        return ""
    s = str(value)
    stripped = s.lstrip()
    if stripped.startswith(("=", "+", "-", "@")):
        return "'" + s
    return s


def write_csv(rows: list[dict], fieldnames: list[str]) -> str:
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        safe = {k: sanitize_csv_cell(r.get(k, "")) for k in fieldnames}
        w.writerow(safe)
    return buf.getvalue()

