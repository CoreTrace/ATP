#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Render the delivered plan: toolchain scenarios plus the CoreTrace GUI plan.

The GUI team delivers its own plan (CoreTrace-GUI_ATP.xlsx, same template) and
its appendices ZIP. Both plans share one workbook so the tester has a single
file: the toolchain tabs are generated as usual, then the GUI rows are appended
to the same two tabs. The GUI plan numbers its scenarios F1, F2...; the
toolchain rows use those numbers for EIP features, so in the merged workbook a
GUI scenario is identified by GUI-F<n>, in the Feature ID column and at the
start of its Feature Name.

    python3 scripts/merge_gui_atp.py [gui.xlsx] [output.xlsx]
"""

from __future__ import annotations

import re
import sys
import zipfile
from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atp_scenarios import ATP_REPO  # noqa: E402
from build_atp_xlsx import (  # noqa: E402
    COLUMNS, ROOT, SCENARIOS, build_info_tab, build_plan_tab,
    info_head, info_line, info_title, write_plan_row,
)

GUI_ZIP = "CoreTrace-GUI_ATP_appendices.zip"
# The GUI plan was written to be delivered on its own, next to its archive. Here the archive is
# in the ATP repository: say so wherever the copied GUI text says otherwise.
GUI_ARCHIVE_WAS = "delivered alongside this workbook"
GUI_ARCHIVE_IS = f"found at the root of the ATP repository ({ATP_REPO})"


GUI_README = "appendices/README.md"
# Added at the top of the GUI README inside the merged archive only: the GUI team's own
# delivery is standalone, here its README is the second document of a larger plan.
GUI_BANNER = (
    "> **Part 2 of the CoreTrace Acceptance Test Plan.** The entry point of the plan is\n"
    f"> `README.md` at the root of the ATP repository ({ATP_REPO}), next to the archive this\n"
    "> file came from: read it first. It describes Part 1 (the analysis toolchain, scenarios\n"
    "> `ENV` to `CORE`) and sends you here for Part 2. In the merged workbook the scenarios\n"
    "> below are named `GUI-F1`, `GUI-F2`...: where this file says `F9`, read `GUI-F9`.\n\n"
)


def link_gui_readme(zip_path: Path) -> bool:
    """Make the README of the GUI archive point back to the entry point of the plan.

    Every entry is copied with its own metadata: the scripts must keep their Unix mode and
    line endings, or ./build.sh is refused on the tester's machine. Returns False when the
    note is already there.
    """
    with zipfile.ZipFile(zip_path) as src:
        entries = [(info, src.read(info.filename)) for info in src.infolist()]
    readme = next(data for info, data in entries if info.filename == GUI_README).decode("utf-8")
    if readme.startswith(GUI_BANNER):
        return False
    with zipfile.ZipFile(zip_path, "w") as dst:
        for info, data in entries:
            if info.filename == GUI_README:
                data = (GUI_BANNER + readme).encode("utf-8")
            dst.writestr(info, data)
    return True


def gui_version(ws_info) -> str:
    """'CoreTrace Desktop v6.0.0-beta.4', read from the Notes of the delivered GUI plan."""
    for row in ws_info.iter_rows(min_col=1, max_col=1, values_only=True):
        found = re.search(r"Version under test:\s*(CoreTrace (?:GUI|Desktop) v[\w.\-]*\w)", str(row[0] or ""))
        if found:
            return found.group(1)
    return "CoreTrace GUI"


def merge_info(ws, gui) -> None:
    version = gui_version(gui)
    ws["B2"] = (f"{ws['B2'].value}; and {version}, the desktop application "
                "(second part of this workbook)")
    ws["C2"] = (f"ATP v1.3 — {date.today().isoformat()} — both parts run in Docker, "
                "on a Linux, macOS or Windows host")

    r = ws.max_row + 2
    r = info_title(ws, r, f"{version} — Acceptance Test Plan")
    r = info_head(ws, r, "Item", "Value", "Notes")
    r = info_line(ws, r, "Product", f"{version}, desktop application over the CoreTrace analyzers",
                  "Its scenarios follow the toolchain scenarios in the Test Plan tab, with the key GUI-F<n>. "
                  "Inside the GUI rows and the GUI appendices, a bare F<n> means GUI-F<n>; in the toolchain "
                  "rows, (F<n>) at the end of a name is an EIP feature number.")
    r = info_line(ws, r, "Appendices", f"{GUI_ZIP}, at the root of the ATP repository ({ATP_REPO})",
                  "Unzip it first: every mention of 'the appendices ZIP' or 'appendices/' in the GUI rows "
                  "below and in the GUI scenarios refers to its appendices/ folder (docker/, datasets/, "
                  "README.md). It is not the archive stored on the Innovation platform.")
    r = info_line(ws, r, "Anomaly reports", "https://github.com/CoreTrace/coretrace-gui/issues",
                  "One issue per anomaly, title prefixed with the GUI-F<n> key. The GUI rows are recorded as "
                  "PASS or FAIL, with the severities of the GUI appendices README (blocking, major, minor).")
    r += 1

    # Copy the GUI Info tab as delivered. Its layout: a bold, single-cell row
    # opens a section; the row after it is that section's header; blank rows
    # separate sections.
    after_title = False
    block_start = True
    for row in gui.iter_rows(min_row=1, max_row=gui.max_row):
        values = [c.value for c in row[:3]]
        if not any(v is not None for v in values):
            r += 1
            after_title = False
            block_start = True
            continue
        first = row[0]
        starts_block, block_start = block_start, False
        if starts_block and first.font.bold and values[1] is None and values[2] is None:
            r = info_title(ws, r, str(values[0]))
            after_title = True
        elif after_title and sum(v is not None for v in values) > 1:
            r = info_head(ws, r, *[str(v) if v is not None else "" for v in values])
            after_title = False
        else:
            r = info_line(ws, r, *[str(v).replace(GUI_ARCHIVE_WAS, GUI_ARCHIVE_IS) if v is not None else ""
                                   for v in values], bold=bool(first.font.bold))


def merge_plan(ws, gui) -> int:
    row = ws.max_row
    count = 0
    for values in gui.iter_rows(min_row=2, max_row=gui.max_row, values_only=True):
        values = list(values[:len(COLUMNS)])
        if values[0] is None:
            continue
        key = f"GUI-{values[0]}"
        values[0] = key
        values[1] = f"{key} · {values[1]}"
        values[8] = ""  # Feedback stays empty for the tester
        row += 1
        count += 1
        write_plan_row(ws, row, [v if v is not None else "" for v in values])
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{row}"
    # The GUI plan carries these two dropdowns; the vocabulary is the one the
    # toolchain rows already use, so they apply to the whole table.
    for col, options in (("C", "Critical feature, Secondary function, User interface, Compatibility"),
                         ("H", "In progress, Done")):
        dv = DataValidation(type="list", formula1=f'"{options}"', allow_blank=True)
        dv.add(f"{col}2:{col}{row}")
        ws.add_data_validation(dv)
    return count


def main() -> int:
    gui_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "CoreTrace-GUI_ATP.xlsx"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "ATP_CoreTrace.xlsx"
    gui = load_workbook(gui_path)

    wb = Workbook()
    wb.remove(wb.active)
    build_info_tab(wb)
    build_plan_tab(wb)
    merge_info(wb["Info & Access"], gui["Info & Access"])
    added = merge_plan(wb["Test Plan"], gui["Test Plan"])
    wb.save(out)
    print(f"{out}  ({len(SCENARIOS)} toolchain + {added} GUI scenarios)")
    if (ROOT / GUI_ZIP).exists() and link_gui_readme(ROOT / GUI_ZIP):
        print(f"{ROOT / GUI_ZIP}  (README now points back to the entry point)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
