#!/usr/bin/env python3
"""Render the pipeline Markdown report as a RTL, print-ready PDF.

The GitHub runner does not provide Microsoft Word/Excel COM automation.  This
renderer keeps the report content produced by ReportingEngine intact and uses
WeasyPrint only for the final presentation layer.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


def inline_markup(value: str) -> str:
    """Convert the small Markdown subset emitted by ReportingEngine to HTML."""

    escaped = html.escape(value, quote=False)
    escaped = re.sub(r"`([^`]+)`", r'<span class="code">\1</span>', escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    return escaped


def is_table_line(value: str) -> bool:
    stripped = value.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def split_cells(value: str) -> list[str]:
    return [part.strip() for part in value.strip().strip("|").split("|")]


def is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", cell.replace(" ", "")) for cell in cells)


def render_markdown(source: str) -> str:
    lines = source.lstrip("\ufeff").splitlines()
    output: list[str] = []
    in_table = False
    in_list = False
    table_header_written = False

    def close_table() -> None:
        nonlocal in_table, table_header_written
        if in_table:
            output.append("</tbody></table>")
            in_table = False
            table_header_written = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            output.append("</ul>")
            in_list = False

    for raw_line in lines:
        line = raw_line.strip()
        # ReportingEngine wraps Markdown in a left-to-right div so that pipe
        # tables are stable in Markdown viewers.  The PDF is intentionally RTL.
        if line in {"<div dir=\"ltr\">", "</div>"}:
            continue

        if is_table_line(line):
            close_list()
            cells = split_cells(line)
            if is_separator_row(cells):
                continue
            if not in_table:
                output.append("<table><thead><tr>")
                output.extend(f"<th>{inline_markup(cell)}</th>" for cell in cells)
                output.append("</tr></thead><tbody>")
                in_table = True
                table_header_written = True
            else:
                output.append("<tr>")
                output.extend(f"<td>{inline_markup(cell)}</td>" for cell in cells)
                output.append("</tr>")
            continue

        close_table()
        if not line:
            close_list()
            continue

        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            close_list()
            level = len(heading.group(1))
            output.append(f"<h{level}>{inline_markup(heading.group(2))}</h{level}>")
            continue

        bullet = re.match(r"^-\s+(.+)$", line)
        if bullet:
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(f"<li>{inline_markup(bullet.group(1))}</li>")
            continue

        close_list()
        output.append(f"<p>{inline_markup(line)}</p>")

    close_table()
    close_list()
    return "\n".join(output)


def build_html(markdown_path: Path, font_path: Path | None) -> str:
    body = render_markdown(markdown_path.read_text(encoding="utf-8-sig"))
    font_face = ""
    if font_path and font_path.exists():
        font_uri = font_path.resolve().as_uri()
        font_face = f"""
        @font-face {{
            font-family: 'B Nazanin Embedded';
            src: url('{font_uri}');
            font-weight: normal;
            font-style: normal;
        }}
        """

    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <style>
    {font_face}
    @page {{
      size: A4 landscape;
      margin: 11mm 10mm 13mm 10mm;
      @bottom-center {{
        content: "گزارش تصمیم‌یار اختیار معامله | صفحه " counter(page);
        font-family: 'B Nazanin Embedded', 'B Nazanin', 'BNazanin',
                     'Noto Naskh Arabic', Tahoma, sans-serif;
        font-size: 9pt;
        color: #5c6670;
      }}
    }}
    :root {{
      font-family: 'B Nazanin Embedded', 'B Nazanin', 'BNazanin',
                   'Noto Naskh Arabic', Tahoma, sans-serif;
      color: #111827;
    }}
    html, body {{
      direction: rtl;
      unicode-bidi: plaintext;
      margin: 0;
      padding: 0;
      font-size: 11pt;
      line-height: 1.45;
    }}
    body {{ text-align: right; }}
    h1, h2, h3 {{
      color: #17365d;
      page-break-after: avoid;
      margin: 0.55em 0 0.28em;
      font-weight: 700;
    }}
    h1 {{ font-size: 20pt; border-bottom: 1px solid #b9c7d5; padding-bottom: 3px; }}
    h2 {{ font-size: 15pt; }}
    h3 {{ font-size: 12.5pt; }}
    p {{ margin: 0.22em 0; }}
    ul {{ margin: 0.2em 0 0.5em; padding-right: 1.4em; }}
    li {{ margin: 0.15em 0; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: auto;
      margin: 0.45em 0 0.8em;
      page-break-inside: auto;
      direction: rtl;
      font-size: 9.2pt;
    }}
    thead {{ display: table-header-group; }}
    tr {{ page-break-inside: avoid; page-break-after: auto; }}
    th, td {{
      border: 0.6pt solid #8292a3;
      padding: 3.5pt 4pt;
      vertical-align: middle;
      text-align: right;
      overflow-wrap: anywhere;
    }}
    th {{
      background: #d9eaf7;
      color: #102a43;
      font-weight: 700;
    }}
    tr:nth-child(even) td {{ background: #f7f9fb; }}
    strong {{ color: #0b3558; }}
    .code {{
      direction: ltr;
      unicode-bidi: embed;
      font-family: 'DejaVu Sans Mono', monospace;
      font-size: 0.88em;
    }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--font-path", type=Path)
    args = parser.parse_args()

    try:
        from weasyprint import HTML
    except ImportError as exc:  # pragma: no cover - exercised in CI
        raise SystemExit(
            "WeasyPrint is required. Install it with: pip install weasyprint"
        ) from exc

    markdown_path = args.markdown.resolve()
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html_text = build_html(markdown_path, args.font_path.resolve() if args.font_path else None)
    HTML(string=html_text, base_url=str(markdown_path.parent)).write_pdf(str(output_path))
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
