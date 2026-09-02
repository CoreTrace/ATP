#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Render the CoreTrace Acceptance Test Plan spreadsheet.

The plan is iterated between test cycles, so it is generated from
`atp_scenarios.py` rather than hand-edited: a scenario change is a data change,
and regenerating never disturbs the layout or drops a column the testers fill.

    python3 scripts/build_atp_xlsx.py [output.xlsx]
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atp_scenarios import SCENARIOS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

BLUE = "0055FF"
LIGHT = "EAF0FF"
GREY = "F5F5F5"
WHITE = "FFFFFF"

HEADER_FONT = Font(bold=True, color=WHITE, size=11)
HEADER_FILL = PatternFill("solid", fgColor=BLUE)
SECTION_FONT = Font(bold=True, color=BLUE, size=11)
SECTION_FILL = PatternFill("solid", fgColor=LIGHT)
TOP_LEFT = Alignment(horizontal="left", vertical="top", wrap_text=True)
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

REPOS = [
    ("coretrace", "Orchestrator CLI + HTTP server: drives every analyzer and merges their reports."),
    ("coretrace-stack-analyzer", "Static analysis of LLVM IR: stack usage, buffer overflows, escapes, uninitialised reads."),
    ("coretrace-concurrency-analyzer", "Static concurrency analysis: data races, missing joins, lock-order deadlocks."),
    ("coretrace-runtime-analyzer", "Instrumented build + execution + runtime event collection (bounds, allocations, vtables)."),
]


def repo_revision(name: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT / name), "describe", "--tags", "--always"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def style_header(ws, row: int, ncols: int) -> None:
    for col in range(1, ncols + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = TOP_LEFT
        cell.border = BOX


def section(ws, row: int, title: str, ncols: int) -> int:
    ws.cell(row=row, column=1, value=title)
    for col in range(1, ncols + 1):
        cell = ws.cell(row=row, column=col)
        cell.fill = SECTION_FILL
        cell.border = BOX
        if col == 1:
            cell.font = SECTION_FONT
            cell.alignment = TOP_LEFT
    return row + 1


def kv(ws, row: int, key: str, value: str, ncols: int = 2) -> int:
    ws.cell(row=row, column=1, value=key).font = Font(bold=True)
    ws.cell(row=row, column=1).alignment = TOP_LEFT
    ws.cell(row=row, column=1).border = BOX
    ws.cell(row=row, column=2, value=value).alignment = TOP_LEFT
    ws.cell(row=row, column=2).border = BOX
    return row + 1


# --------------------------------------------------------------- tab 1


def build_info_tab(wb: Workbook) -> None:
    ws = wb.create_sheet("Info & Access")
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 118

    r = 1
    ws.cell(row=r, column=1, value="CoreTrace — Acceptance Test Plan").font = Font(bold=True, size=16, color=BLUE)
    r += 2

    r = section(ws, r, "1. PROJECT", 2)
    r = kv(ws, r, "Project", "CoreTrace — static and dynamic analysis toolchain for C/C++")
    r = kv(ws, r, "Product type", "Command-line tools + HTTP analysis server + GitHub Action. No graphical interface: "
                                  "the deliverable is evaluated through its CLI, its reports (human / JSON / SARIF) and its exit codes.")
    r = kv(ws, r, "Organisation", "github.com/CoreTrace")
    r = kv(ws, r, "ATP version", f"1.0 — {date.today().isoformat()}")
    r = kv(ws, r, "Tester profile", "Any developer comfortable with a terminal. No knowledge of the CoreTrace internals "
                                    "is required: every scenario is a copy-pasteable command with a checkable output.")
    r += 1

    r = section(ws, r, "2. REPOSITORIES UNDER TEST", 2)
    for name, purpose in REPOS:
        r = kv(ws, r, name, f"https://github.com/CoreTrace/{name}  —  revision under test: {repo_revision(name)}\n{purpose}")
    r = kv(ws, r, "Access", "Public repositories, clone over HTTPS. No account, licence key or credential is needed: "
                            "CoreTrace analyses local source files and stores nothing remotely. The "
                            '"account / identifier / password" data set of the ATP template does not apply.')
    r += 1

    r = section(ws, r, "3. TEST ENVIRONMENTS", 2)
    r = kv(ws, r, "Supported platforms", "macOS 14+ (Apple Silicon or Intel) natively, and Linux (Ubuntu 24.04) through Docker. "
                                         "Both run the same scenario commands; only the setup differs.")
    r = kv(ws, r, "Toolchain", "LLVM / Clang 20, CMake 3.22+, Ninja, Python 3.10+, cppcheck, Docker (for the Linux path). "
                               "The analyzers link against LLVM 20; another major version will not configure.")
    r = kv(ws, r, "macOS setup", "brew install cmake ninja llvm@20 cppcheck\n"
                                 "./atp.sh doctor        # checks every prerequisite, names what is missing\n"
                                 "./atp.sh build-macos   # builds the four tools (~15 min)\n"
                                 "See scenario ENV-01.")
    r = kv(ws, r, "Linux setup (Docker)", "./atp.sh build-linux   # builds coretrace-atp:latest, ~30-60 min, needs network access\n"
                                          "./atp.sh linux         # shell inside the image, sources and binaries already at /atp\n"
                                          "The image is Ubuntu 24.04 + LLVM 20 with the four tools pre-built. It runs unprivileged "
                                          "(uid 1000): several concurrency tests assert that an unreadable path fails, and root "
                                          "reads it regardless. See scenario ENV-02.")
    r = kv(ws, r, "Working directory", "Every scenario command is written to be pasted from the ATP root — the folder holding the "
                                       "four repositories on macOS, /atp inside the container. Each scenario starts with the "
                                       "`cd <repository>` it needs.")
    r = kv(ws, r, "Offline note", "The first build of either environment downloads LLVM packages and fetches coretrace-compiler, "
                                  "coretrace-logger and coretrace-stack-analyzer through CMake. After that, every scenario runs offline.")
    r += 1

    r = section(ws, r, "4. DATA SETS", 2)
    r = kv(ws, r, "Nature of the data", "CoreTrace analyses source code, so the data sets are C/C++ corpora shipped inside the "
                                        "repositories — no database, no user accounts, no seed script. They are versioned with "
                                        "the code, so a tester always gets the corpus matching the revision under test.")
    r = kv(ws, r, "Vulnerable corpus (true positives)",
           "coretrace-stack-analyzer/test/security/ — 15 categories, one directory each: buffer-overflow, use-after-free, "
           "stack-escape, uninitialized, integer-overflow, null-dereference, format-string, command-injection, oob-read, "
           "memory-leak, toctou, type-confusion, unsafe-functions, variadic-mismatch, sizeof-pitfall. Each file must produce "
           "a specific diagnostic.")
    r = kv(ws, r, "Concurrency corpus",
           "coretrace-concurrency-analyzer/tests/fixtures/concurrency/ — data-race/, missing-join/, deadlock/, "
           "condition-variable/, memory-barrier/, in C and C++, pthread and std::thread. A filename ending in _no_fp, "
           "_no_diagnostic or _no_missing_join is a negative case that must stay silent.")
    r = kv(ws, r, "Runtime corpus",
           "coretrace-runtime-analyzer/test/ — 31 instrumented programs: allocation lifecycle (ct_alloc_*, ct_autofree_*), "
           "new/delete variants, virtual dispatch (ct_vtable_*), bounds violations. Each is compiled, run and observed.")
    r = kv(ws, r, "Clean corpus (must stay silent)",
           "coretrace-stack-analyzer/test/no-error/ and the 15 files listed in datasets/stack-no-false-positive.txt "
           "(shipped in this appendix). These carry the false-positive contract and are used by scenario STACK-11.")
    r = kv(ws, r, "Full expectation set",
           "Most fixtures embed their expected diagnostics as `// at line X, column Y` comments read by "
           "coretrace-stack-analyzer/run_test.py (1711 assertions) and as EXPECT-HUMAN-DIAGNOSTICS blocks read by the "
           "concurrency golden tests. Scenarios STACK-12 and CONC-08 run those suites end to end.")
    r += 1

    r = section(ws, r, "5. APPENDICES", 2)
    r = kv(ws, r, "Content of the ZIP", "atp.sh (single entry point), docker/Dockerfile (Linux image), "
                                        "datasets/ (the false-positive list), README.md (tester guide), this spreadsheet.")
    r = kv(ws, r, "Size", "Under 1 MB. The corpora are not duplicated in the archive: they live in the repositories, "
                          "which the tester clones anyway, so they can never drift out of sync with the code under test.")
    r += 1

    r = section(ws, r, "6. VALIDATION CRITERIA", 2)
    r = kv(ws, r, "A scenario is OK when", "Every element of the Expected result column is observed, in the stated order, with no "
                                           "error other than the ones the scenario itself describes as expected, and no crash, hang "
                                           "or non-zero exit code beyond those it names.")
    r = kv(ws, r, "A scenario is KO when", "Any expected element is missing or different; or the tool crashes, hangs beyond the stated "
                                           "duration, or returns an unexpected exit code. Partial success is KO — record what did work "
                                           "in Feedback.")
    r = kv(ws, r, "Blocking anomaly", "Prevents the scenario from being executed at all (build failure, crash on start, hang). "
                                      "Blocks the release: reported the same day.")
    r = kv(ws, r, "Critical anomaly", "The scenario runs but the result is wrong in a way that misleads a user: a missed "
                                      "vulnerability (false negative), a wrong location, a false positive on the clean corpus, "
                                      "a wrong exit code in CI. Fixed before Epitech Experience.")
    r = kv(ws, r, "Minor anomaly", "Wording, formatting, log noise, cosmetic defects. Backlogged.")
    r += 1

    r = section(ws, r, "7. ANOMALY HANDLING", 2)
    r = kv(ws, r, "Where to report", "One GitHub issue per anomaly, in the repository named in the Component column of the scenario. "
                                     "Title prefixed with the scenario id, e.g. `[STACK-05] index off by one not reported`.")
    r = kv(ws, r, "What to include", "Scenario id, platform (macOS or Linux image), the exact command, the full output, "
                                     "and the output of `./atp.sh versions` so the revision is unambiguous.")
    r = kv(ws, r, "Already-known defects", "Three scenarios document a known defect in their Expected result: CORE-04 and CORE-08 "
                                           "(cppcheck is invoked through a hardcoded Homebrew path, so it cannot run on Linux) and "
                                           "RUN-05 (instrumented binaries abort at teardown on macOS). Do not open new issues for "
                                           "these: mark the scenario KO and quote the line.")
    r = kv(ws, r, "Cycle", "Each cycle: the team ships a revision, testers run the plan and fill Verdict + Feedback, anomalies are "
                           "triaged by severity, the plan is regenerated from scripts/ (a scenario is a data edit) and the next "
                           "cycle starts. Scenarios marked 'In progress' are expected to move to 'Done' as the defects close.")

    for row in ws.iter_rows(min_row=1, max_row=r, max_col=2):
        for cell in row:
            if cell.alignment.horizontal is None:
                cell.alignment = TOP_LEFT
    ws.freeze_panes = "A2"


# --------------------------------------------------------------- tab 2

COLUMNS = [
    ("Feature ID", 12),
    ("Component", 30),
    ("Feature Name", 34),
    ("Category", 18),
    ("Objective", 46),
    ("Prerequisites", 42),
    ("Steps", 66),
    ("Expected result", 74),
    ("Development status", 18),
    ("Platform", 22),
    ("Verdict (OK/KO)", 15),
    ("Feedback (tester)", 46),
]


def build_plan_tab(wb: Workbook) -> None:
    ws = wb.create_sheet("Test Plan")
    for idx, (title, width) in enumerate(COLUMNS, start=1):
        ws.cell(row=1, column=idx, value=title)
        ws.column_dimensions[get_column_letter(idx)].width = width
    style_header(ws, 1, len(COLUMNS))

    verdict = DataValidation(type="list", formula1='"OK,KO,Not run"', allow_blank=True)
    ws.add_data_validation(verdict)

    for offset, sc in enumerate(SCENARIOS):
        row = offset + 2
        steps = "\n".join(f"{i}. {c}" if not c.startswith("#") else c
                          for i, c in enumerate(sc["steps"], start=1))
        values = [
            sc["id"], sc["component"], sc["name"], sc["category"], sc["objective"],
            sc["prerequisites"], steps, sc["expected"], sc["status"], sc["platform"], "", "",
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.alignment = TOP_LEFT
            cell.border = BOX
            if offset % 2:
                cell.fill = PatternFill("solid", fgColor=GREY)
        verdict.add(ws.cell(row=row, column=11))
        # Row height is left to the reader: openpyxl cannot measure wrapped
        # text, and a guessed height clips content in some viewers.

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{len(SCENARIOS) + 1}"


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "ATP_CoreTrace.xlsx"
    wb = Workbook()
    wb.remove(wb.active)
    build_info_tab(wb)
    build_plan_tab(wb)
    wb.save(out)
    print(f"{out}  ({len(SCENARIOS)} scenarios)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
