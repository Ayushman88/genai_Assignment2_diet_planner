import io
import re
from typing import List
from docx import Document
from docx.shared import Pt, RGBColor


def export_to_txt(plan_markdown: str, title: str = "Weekly Diet Plan") -> bytes:
    """Convert generated diet plan markdown into a clean plain-text (.txt) byte payload."""
    heading = title.strip() or "Weekly Diet Plan"
    lines = [heading, "=" * len(heading), ""]

    for raw_line in plan_markdown.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            sub = line[3:].strip()
            lines.append(sub.upper())
            lines.append("-" * len(sub))
        elif line.startswith("### "):
            lines.append(line[4:].strip())
        else:
            lines.append(line.replace("**", ""))

    return ("\n".join(lines).strip() + "\n").encode("utf-8")


def export_to_docx(plan_markdown: str, title: str = "Weekly Diet Plan") -> bytes:
    """Convert generated diet plan markdown (including 7-day table) into a Word (.docx) payload."""
    doc = Document()

    title_heading = doc.add_heading(title.strip() or "Weekly Diet Plan", level=0)
    title_heading.runs[0].font.color.rgb = RGBColor(0x16, 0x65, 0x34)

    lines = plan_markdown.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Detect Markdown table block
        if line.startswith("|") and line.endswith("|"):
            table_lines: List[str] = []
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            _add_markdown_table(doc, table_lines)
            continue

        if line.startswith("## "):
            doc.add_heading(line[3:].strip(), level=1)
        elif line.startswith("### "):
            doc.add_heading(line[4:].strip(), level=2)
        elif line.startswith("- ") or line.startswith("* "):
            para = doc.add_paragraph(style="List Bullet")
            _add_formatted_runs(para, line[2:].strip())
        else:
            para = doc.add_paragraph()
            _add_formatted_runs(para, line)

        i += 1

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def _add_markdown_table(doc: Document, table_lines: List[str]) -> None:
    """Parse a Markdown table and render it as a styled Word table."""
    parsed_rows: List[List[str]] = []
    for row_line in table_lines:
        cells = [c.strip() for c in row_line.strip("|").split("|")]
        # Skip separator rows like | --- | --- |
        if all(re.fullmatch(r":?-{2,}:?", cell) or cell == "" for cell in cells):
            continue
        parsed_rows.append(cells)

    if not parsed_rows:
        return

    num_cols = max(len(r) for r in parsed_rows)
    table = doc.add_table(rows=len(parsed_rows), cols=num_cols)
    table.style = "Table Grid"

    for r_idx, row_cells in enumerate(parsed_rows):
        for c_idx in range(num_cols):
            cell_text = row_cells[c_idx] if c_idx < len(row_cells) else ""
            cell = table.cell(r_idx, c_idx)
            para = cell.paragraphs[0]
            para.text = ""
            if r_idx == 0:
                run = para.add_run(cell_text.replace("**", ""))
                run.bold = True
                run.font.size = Pt(10)
            else:
                _add_formatted_runs(para, cell_text)


def _add_formatted_runs(paragraph, text: str) -> None:
    """Render **bold** markdown spans cleanly inside a python-docx paragraph."""
    parts = re.split(r"(\*\*.*?\*\*)", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        else:
            paragraph.add_run(part)
