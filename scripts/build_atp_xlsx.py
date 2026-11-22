#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Render the CoreTrace Acceptance Test Plan spreadsheet.

The plan is iterated between test cycles, so it is generated from
`atp_scenarios.py` rather than hand-edited: a scenario change is a data change,
and regenerating never disturbs the layout or drops a column the testers fill.

    python3 scripts/build_atp_xlsx.py [output.xlsx]
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atp_scenarios import ATP_REPO, FEATURES, SCENARIOS  # noqa: E402

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

# (repository, purpose, name of the ARG in docker/Dockerfile that fixes its revision)
REPOS = [
    ("coretrace", "Orchestrator CLI + HTTP server: drives the analyzers and merges their reports.", "CORETRACE_REF"),
    ("coretrace-stack-analyzer", "Static analysis of LLVM IR: stack usage, buffer overflows, escapes, uninitialised reads.", "STACK_REF"),
    ("coretrace-concurrency-analyzer", "Static concurrency analysis: data races, missing joins, lock-order deadlocks.", "CONCURRENCY_REF"),
    ("coretrace-runtime-analyzer", "Instrumented build + execution + runtime event collection (bounds, allocations, vtables).", "RUNTIME_REF"),
]


def repo_revision(arg: str) -> str:
    """The revision under test: docker/Dockerfile is its single source of truth."""
    found = re.search(rf"^ARG {arg}=(\S+)", (ROOT / "docker" / "Dockerfile").read_text(), re.M)
    ref = found.group(1) if found else "unknown"
    return ref[:12] if re.fullmatch(r"[0-9a-f]{40}", ref) else ref


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


def info_title(ws, row: int, text: str) -> int:
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = Font(bold=True, color=WHITE, size=11)
    for col in range(1, 4):
        ws.cell(row=row, column=col).fill = HEADER_FILL
        ws.cell(row=row, column=col).border = BOX
    return row + 1


def info_head(ws, row: int, *labels: str) -> int:
    for col, label in enumerate(labels, start=1):
        cell = ws.cell(row=row, column=col, value=label)
        cell.font = Font(bold=True)
        cell.fill = SECTION_FILL
        cell.alignment = TOP_LEFT
        cell.border = BOX
    return row + 1


def info_line(ws, row: int, *values: str, bold: bool = False) -> int:
    for col, value in enumerate(values, start=1):
        cell = ws.cell(row=row, column=col, value=value)
        cell.alignment = TOP_LEFT
        cell.border = BOX
        if bold and col == 1:
            cell.font = Font(bold=True)
    return row + 1


def build_info_tab(wb: Workbook) -> None:
    """Tab 1, on the skeleton of ATP_template.xlsx.

    The template opens with two fixed tables — "Access to testing platforms"
    (Acess point / URL) and "Data sets" (Account type / Identifier / Password).
    Both are kept at the top, with their exact titles and header wording, so
    the delivered file lines up with the template. The subject also requires
    acceptance criteria and an anomaly strategy, which the skeleton has no room
    for, so further sections follow in the same three-column style.
    """
    ws = wb.create_sheet("Info & Access")
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 78
    ws.column_dimensions["C"].width = 60

    def title(row: int, text: str) -> int:
        return info_title(ws, row, text)

    def head(row: int, *labels: str) -> int:
        return info_head(ws, row, *labels)

    def line(row: int, *values: str) -> int:
        return info_line(ws, row, *values)

    r = 1
    cell = ws.cell(row=r, column=1, value="CoreTrace — Acceptance Test Plan")
    cell.font = Font(bold=True, size=16, color=BLUE)
    r = line(r + 1, "Project", "CoreTrace — static and dynamic analysis toolchain for C/C++",
             f"ATP v1.3 — {date.today().isoformat()} — Linux")
    r = line(r, "Start here",
             f"Everything needed to run this plan is in one public repository: {ATP_REPO}\n"
             f"1. Get it: git clone {ATP_REPO}.git   (or, on its GitHub page: Code, then Download ZIP)\n"
             "2. Open README.md at the root of the folder you get: it is the entry point of the plan, it "
             "describes the two parts and says which document to open next.",
             "Do not use the appendices archive stored on the Innovation platform: it belongs to an earlier "
             "version of the plan and no longer matches this workbook. Part 1, the analysis toolchain: keys "
             "ENV, STACK, CONC, RUN, CORE, first rows of the Test Plan tab. Part 2, the desktop application: "
             "keys GUI-F..., last rows of the tab, with its own instructions in the GUI archive of the "
             "repository.")
    r = line(r, "Feature ID column",
             "A unique key per scenario: ENV (environment), STACK (coretrace-stack-analyzer), CONC "
             "(coretrace-concurrency-analyzer), RUN (coretrace-runtime-analyzer), CORE (coretrace). Quote it "
             "in Feedback and in issues.",
             "Where a scenario exercises a numbered EIP feature, the number ends its Feature Name, e.g. "
             "(F10). Several scenarios can share one EIP feature; the table 'EIP features and their "
             "scenarios' below lists them.")
    r = line(r, "Product type",
             "Command-line tools and an HTTP analysis server, with no user account: this part of the "
             "product is evaluated through its CLI, its reports (human / JSON / SARIF) and its exit codes.",
             "For these scenarios a tester needs only a terminal: every step is a command to paste. "
             "GUIDE_TESTEUR.md in the ATP repository lists the same commands as plain text blocks, easier to copy "
             "than a spreadsheet cell.")
    r += 1

    # --- template table 1 ----------------------------------------------------
    r = title(r, "Access to testing platforms")
    r = head(r, "Acess point", "URL", "Notes")
    for name, purpose, arg in REPOS:
        r = line(r, name, f"https://github.com/CoreTrace/{name}",
                 f"{purpose} Revision under test: {repo_revision(arg)}")
    r = line(r, "ATP repository (test harness)", ATP_REPO,
             "README.md, GUIDE_TESTEUR.md, atp.sh, docker/, datasets/, proofs/ and the GUI archive. Clone "
             "it, open a terminal in its folder and run ./atp.sh build-linux. The four repositories above "
             "are not to be cloned by hand: the image fetches them at the revisions under test.")
    r = line(r, "Linux test image", "built locally with ./atp.sh build-linux (Dockerfile in the ATP repository)",
             "Ubuntu 24.04 + LLVM 20 with the four tools prebuilt. Not published to a registry: it is "
             "reproducible from the repository in one command.")
    r = line(r, "Credentials", "none",
             "Public repositories, cloned over HTTPS. CoreTrace analyses local source files and sends nothing "
             "anywhere, so there is no account, licence key or token to hand out.")
    r += 1

    # --- template table 2 ----------------------------------------------------
    r = title(r, "Data sets")
    r = head(r, "Account type", "Identifier", "Password")
    r = line(r, "Not applicable", "—", "—")
    r = line(r, "Why",
             "CoreTrace has no authentication, no database and no user roles: it is a compiler-side analysis "
             "toolchain. Its data sets are C/C++ source corpora, listed in the next section.", "")
    r += 1

    r = title(r, "Data sets — source corpora")
    r = head(r, "Corpus", "Location", "Role in the plan")
    r = line(r, "Vulnerable code (true positives)", "coretrace-stack-analyzer/test/security/",
             "15 categories, one directory each: buffer-overflow, use-after-free, stack-escape, uninitialized, "
             "integer-overflow, null-dereference, format-string, command-injection, oob-read, memory-leak, "
             "toctou, type-confusion, unsafe-functions, variadic-mismatch, sizeof-pitfall. Each category has "
             "its own diagnostic, listed by scenario STACK-17; memory-leak and use-after-free report once the "
             "resource model is given (--resource-model).")
    r = line(r, "Stack behaviour", "coretrace-stack-analyzer/test/ (vla, recursion, local-storage, alloca, "
             "escape-stack, cpy-buffer, ...)",
             "Frame sizing, call-chain propagation, dynamic allocation, recursion, pointer escape.")
    r = line(r, "Concurrency", "coretrace-concurrency-analyzer/tests/fixtures/concurrency/",
             "13 folders, among them data-race/, deadlock/, missing-join/, condition-variable/, "
             "thread-escape/ and use-after-free/, in C and C++, pthread and std::thread. A name ending in "
             "_no_fp, _no_diagnostic or _no_missing_join promises that one rule stays silent; the 28 files "
             "that must produce no diagnostic at all are listed in datasets/conc-no-false-positive.txt.")
    r = line(r, "Runtime", "coretrace-runtime-analyzer/test/",
             "32 instrumented programs: allocation lifecycle (ct_alloc_*, ct_autofree_*), new/delete variants, "
             "virtual dispatch (ct_vtable_*); plus test/findings/, seven programs whose header states the "
             "finding the analyzer must report (scenario RUN-08). Each is compiled, executed and observed.")
    r = line(r, "Must stay silent", "datasets/stack-no-false-positive.txt and "
             "datasets/conc-no-false-positive.txt (in the ATP repository); coretrace-stack-analyzer/test/no-error/",
             "The false-positive contract, used by scenarios STACK-10, STACK-11 and CONC-05. Fixtures that "
             "reproduce one false positive while still containing a real defect are deliberately left out of "
             "the two lists: they legitimately emit diagnostics.")
    r = line(r, "Embedded expectations", "// at line X, column Y comments, and EXPECT-HUMAN-DIAGNOSTICS blocks",
             "Read by run_test.py (2916 checks), by the concurrency suites and by the runtime fixtures check. "
             "Scenarios STACK-12, CONC-08 and RUN-09 run those suites end to end.")
    r = line(r, "Why the corpora are not in the ATP repository",
             "They are versioned inside the repositories, which the image clones at the revision under test.",
             "Copying them there would let them drift out of sync with the code under test, and "
             "a scenario would then check the wrong expectation.")
    r += 1

    r = title(r, "EIP features and their scenarios")
    r = head(r, "Feature", "Name", "Scenarios")
    for number, name in FEATURES.items():
        r = line(r, number, name, ", ".join(sc["id"] for sc in SCENARIOS if sc.get("eip") == number))
    r = line(r, "No feature number", "Environment, robustness and regression checks that span several features",
             ", ".join(sc["id"] for sc in SCENARIOS if not sc.get("eip")))
    r += 1

    r = title(r, "Test environments")
    r = head(r, "Item", "Linux (Docker)", "Notes")
    r = line(r, "Supported", "Ubuntu 24.04 image, built locally",
             "The toolchain scenarios run on Linux only, inside this image. No dedicated scenario covers "
             "native macOS builds, the third-party analyzers ctrace can drive (cppcheck, flawfinder, ikos, "
             "tscancode) or coretrace-python-analyzer.")
    r = line(r, "Setup",
             "./atp.sh build-linux   (6 min 30 s measured on 8 cores, needs network)\n./atp.sh linux   (shell at /atp)",
             "Docker must be running on the host, with at least 4 CPUs, 8 GB of memory and 10 GB of free "
             "disk space. README.md says what to do if the build fails.")
    r = line(r, "Toolchain", "LLVM/Clang 20, clang-format 20, CMake 3.28, Ninja, Python 3.12, pytest, cppcheck, flawfinder",
             "Preinstalled in the image.")
    r = line(r, "Scenario commands", "Run each scenario from /atp; its first cd selects the repository.",
             "Return to /atp before starting the next scenario.")
    r = line(r, "Privileges", "ubuntu (uid 1000)",
             "Run unprivileged: permission-denied tests must fail on unreadable paths.")
    r = line(r, "Revisions under test",
             "Fixed in docker/Dockerfile (ARG *_REF), listed in the first table above. `cat /atp/VERSIONS` "
             "in the container, or `./atp.sh versions` on the host, prints what the image was built from.",
             "Each repository pins its own coretrace-compiler and coretrace-log versions; CMake fetches "
             "them while the image builds.")
    r = line(r, "Offline", "The image build needs network access. Every scenario then runs offline.",
             "The scenarios run against the tools, sources and data included in the image.")
    r += 1

    r = title(r, "Validation criteria")
    r = head(r, "Verdict", "Rule", "How to record it")
    r = line(r, "OK", "Every element of the Expected results column is observed, with no error, crash, hang or "
             "unexpected exit code other than those the scenario itself describes as expected.",
             "Write `OK` at the start of the Feedback cell.")
    r = line(r, "KO", "Any expected element missing or different; or a crash, a hang beyond the stated "
             "duration, or an unexpected exit code. Partial success counts as KO.",
             "Write `KO` then what you actually saw, even partially.")
    r = line(r, "Not run", "A prerequisite is unavailable, for example ENV-02 failed.",
             "Write `Not run` and the reason.")
    r += 1

    r = title(r, "Anomaly handling")
    r = head(r, "Severity", "Definition", "Treatment")
    r = line(r, "Blocking", "Prevents the scenario from running at all: build failure, crash on start, hang.",
             "Reported the same day; blocks the release.")
    r = line(r, "Critical", "The scenario runs but the result misleads a user: a missed vulnerability, a wrong "
             "location, a false positive on the clean corpus, a wrong CI exit code.",
             "Fixed before Epitech Experience.")
    r = line(r, "Minor", "Wording, formatting, log noise, cosmetics.", "Backlogged.")
    r = line(r, "Where to report", "One GitHub issue per anomaly, in the repository the scenario key names: "
             "STACK coretrace-stack-analyzer, CONC coretrace-concurrency-analyzer, RUN "
             "coretrace-runtime-analyzer, CORE and ENV coretrace.",
             "Title prefixed with the scenario key, e.g. `[STACK-05] index off by one not reported`. Include "
             "the platform, the exact command, the full output and `./atp.sh versions`.")
    r = line(r, "Already-known defects",
             f"None in the toolchain scenarios at the revisions under test: the {len(SCENARIOS)} scenarios "
             "pass in the reference image.",
             "A toolchain scenario that fails is therefore an anomaly: report it. An exit code 2 from ctrace "
             "is not a failure when the scenario expects it: it is the code ctrace returns when it finds an "
             "error-level defect.")
    r = line(r, "Cycle", "Ship a revision, testers fill Feedback, anomalies are triaged by severity, the plan "
             "is regenerated from scripts/ and the next cycle starts.",
             "A scenario marked 'In progress' covers a feature still being developed; it moves to 'Done' "
             "when the feature is complete.")

    ws.freeze_panes = "A2"


# --------------------------------------------------------------- tab 2

# Exactly the columns of ATP_template.xlsx, in its order, with its spellings
# ("Developpement status" is the template's own typo, kept so the delivered
# file diffs cleanly against the template). Widths are the template's too.
COLUMNS = [
    ("Feature ID", 12.2),
    ("Feature Name", 29.0),
    ("Category", 16.8),
    ("Objective", 34.3),
    ("Prerequisites", 29.5),
    ("Steps", 29.7),
    ("Expected results", 61.2),
    ("Developpement status", 22.5),
    ("Feedback", 36.0),
]


def render_steps(steps: list[str]) -> list[str]:
    """Number the commands, leave comment lines unnumbered.

    Numbering comments too would make the visible numbers skip, and the
    Prerequisites column refers to steps by number.
    """
    out, n = [], 0
    for step in steps:
        if step.startswith("#"):
            out.append(step)
        else:
            n += 1
            out.append(f"{n}. {step}")
    return out


def build_plan_tab(wb: Workbook) -> None:
    ws = wb.create_sheet("Test Plan")
    for idx, (title, width) in enumerate(COLUMNS, start=1):
        ws.cell(row=1, column=idx, value=title)
        ws.column_dimensions[get_column_letter(idx)].width = width
    style_header(ws, 1, len(COLUMNS))

    # The template has no tester dropdown, so Feedback stays free text; the
    # OK/KO convention is stated on the Info tab.
    for offset, sc in enumerate(SCENARIOS):
        row = offset + 2
        # Component and platform have no column in the template. Put the
        # scenario key in Feature Name (testers quote it in issues) and the
        # platform in Prerequisites, where it belongs anyway.
        eip = sc.get("eip")
        name = sc["name"] if not eip or f"({eip})" in sc["name"] else f"{sc['name']} ({eip})"
        values = [
            sc["id"],
            f"{sc['id']} \u00b7 {name}",
            sc["category"],
            sc["objective"],
            f"{sc['prerequisites']}\nPlatform: {sc['platform']}",
            "\n".join(render_steps(sc["steps"])),
            sc["expected"],
            sc["status"],
            "",
        ]
        write_plan_row(ws, row, values)

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{len(SCENARIOS) + 1}"


def write_plan_row(ws, row: int, values: list[str]) -> None:
    """One scenario row; even rows (offset from the header) are shaded grey."""
    for col, value in enumerate(values, start=1):
        cell = ws.cell(row=row, column=col, value=value)
        cell.alignment = TOP_LEFT
        cell.border = BOX
        if row % 2:
            cell.fill = PatternFill("solid", fgColor=GREY)


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
