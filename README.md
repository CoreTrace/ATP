# CoreTrace — Acceptance Test Plan

**Start here.** This is the first file to open. It is the entry point of the
whole plan: it says what the plan contains, which document to open next, and
when.

This repository holds everything needed to run the plan. The workbook
delivered on the Innovation platform sends you here; the appendices archive
stored on that platform belongs to an earlier version of the plan and must not
be used.

## Get the repository

```bash
git clone https://github.com/CoreTrace/ATP.git
cd ATP
```

Without git: on <https://github.com/CoreTrace/ATP>, click **Code**, then
**Download ZIP**, unzip it and open a terminal in the folder you get
(`ATP-main`).

## The plan at a glance

The plan has two parts. They are independent — separate Docker images, no
shared step — and can be run in either order. Both are recorded in the same
workbook, `ATP_CoreTrace.xlsx`, tab *Test Plan*: Part 1 first, then Part 2.

| | Part 1 — Analysis toolchain | Part 2 — Desktop application |
|---|---|---|
| What you test | Four command-line tools, from a terminal | CoreTrace Desktop, from your browser |
| Scenarios | 44, keys `ENV`, `STACK`, `CONC`, `RUN`, `CORE` | 24, keys `GUI-F1` to `GUI-F24` |
| Instructions | **This file**, sections 1 to 4 | `appendices/README.md`, inside `CoreTrace-GUI_ATP_appendices.zip` (section 5 shows how to get there) |
| Commands | `GUIDE_TESTEUR.md`, ready to copy | The steps of the *Test Plan* tab |
| Environment | `./atp.sh build-linux`, then `./atp.sh linux` | Its own `./build.sh`, then `./run.sh` |
| Verdict to write in Feedback | `OK`, `KO` or `Not run` | `PASS` or `FAIL` |

### Which file to open, and when

1. `README.md`, this file — now.
2. `ATP_CoreTrace.xlsx`, the workbook — read *Info & Access* once, then keep
   *Test Plan* open: every verdict is written there.
3. `GUIDE_TESTEUR.md` — while you run Part 1.
4. `appendices/README.md`, from the GUI archive — when you start Part 2. From
   that point on it replaces sections 1 to 4 of this file, which apply to
   Part 1 only.

### What this repository contains

```
ATP/
├── README.md                           ← this file, the entry point
├── ATP_CoreTrace.xlsx                  ← the workbook, both parts
├── GUIDE_TESTEUR.md                    ← Part 1: the commands of every scenario (in French)
├── atp.sh  docker/  datasets/  proofs/ ← Part 1: the test environment
├── CoreTrace-GUI_ATP_appendices.zip    ← Part 2: its own README, environment and data set
└── scripts/  CoreTrace-GUI_ATP.xlsx    ← for the CoreTrace team, not needed to test
```

## Part 1 — the analysis toolchain

CoreTrace is a static and dynamic analysis toolchain for C/C++, made of four
repositories:

| Repository | What it does | Scenarios |
|---|---|---|
| `coretrace-stack-analyzer` | Static analysis on LLVM IR: stack usage, buffer overflows, pointer escapes, uninitialised reads. | `STACK-*` |
| `coretrace-concurrency-analyzer` | Static concurrency analysis: data races, missing joins, lock-order deadlocks. | `CONC-*` |
| `coretrace-runtime-analyzer` | Builds an instrumented binary, runs it, collects runtime events. | `RUN-*` |
| `coretrace` | Orchestrator CLI and HTTP server; drives the analyzers and merges their reports. | `CORE-*` |

These tools have no account to create and nothing to install on your machine:
they are built inside a Docker image and tested from a terminal.

### 1. What you need

- A macOS or Linux machine. On Windows, use WSL 2: `atp.sh` is a bash script.
- Docker Desktop or Docker Engine, **started**, with at least 4 CPUs and 8 GB
  of memory (Docker Desktop: Settings → Resources).
- 10 GB of free disk space.
- Network access to GitHub and apt.llvm.org while the image builds.

You do not need a compiler or the CoreTrace sources: the image fetches the
four repositories itself, at the revisions the plan was written for.

### 2. Build and enter the test environment

Open a terminal **in the folder of this repository** (the one holding this
file), then:

```bash
./atp.sh build-linux    # about 7 min on an 8-core laptop, up to 30 on a slower one; needs network
./atp.sh linux          # opens a shell inside the image, in /atp
```

The first command ends with `==> done — open a shell with: ./atp.sh linux`.
After the second one your prompt becomes `ubuntu@…:/atp$`: every scenario
command is typed there. Leaving the shell (`exit`) discards the container;
`./atp.sh linux` opens a fresh one, nothing has to be rebuilt.

If `./atp.sh build-linux` fails:

- `permission denied: ./atp.sh` — the unzip tool dropped the execute bit; run
  `chmod +x atp.sh`, then retry.
- `the Docker daemon is not running` — start Docker, then retry.
- A download error (`Could not resolve host`, `Failed to fetch`, `429`) — the
  network dropped; run the same command again, finished steps are reused.
- `Killed` or `c++: fatal error` during a compile step — Docker ran out of
  memory; run `ATP_JOBS=4 ./atp.sh build-linux`.
- Anything else — stop there. Mark `ENV-02` **KO** with the last 30 lines of
  output and every other toolchain scenario **Not run**.

### 3. Run the scenarios

Open `ATP_CoreTrace.xlsx` (the same workbook as the one delivered on the platform).

- **Info & Access** — environments, data sets, validation criteria, how to
  report an anomaly.
- **Test Plan** — the Part 1 scenarios, then the Part 2 scenarios.
  Start with `ENV-02`: everything else in Part 1 depends on it. Its first four
  steps — getting the repository, then the two commands of section 2 — are
  already done; continue with its fifth step, inside the container.

The 44 toolchain scenarios need about 7 minutes of machine time in total; the
longest is `CONC-08` (3 minutes). The rest is reading and copying.

Every step is a command to paste in the container, from `/atp`; each scenario
begins with the `cd` it needs. `GUIDE_TESTEUR.md` (in French) lists the same
commands as plain text blocks: copy them from there rather than from a
spreadsheet cell, which adds quotes around multi-line text.

Fill in **Feedback** for each row, starting with `OK`, `KO` or `Not run`:

- **OK** — every element of *Expected results* is observed.
- **KO** — anything differs; write down what you saw, even partially.
- **Not run** — a prerequisite is unavailable; give the reason.

No defect is known in the toolchain scenarios at the revisions under test: a
scenario that fails is an anomaly, report it. One thing is not a failure:
`ctrace` exits with code 2 when it finds an error-level defect, and a few
`CORE` scenarios expect exactly that.

### 4. Reporting an anomaly

One GitHub issue per anomaly, in the repository named by the scenario key
(table above; `ENV` goes to `coretrace`), titled with the key — for example
`[STACK-05] index off by one not reported`. Include your platform, the exact
command, the full output, and the output of:

```bash
./atp.sh versions       # on your machine; or: cat /atp/VERSIONS in the container
```

## Part 2 — the desktop application

### 5. Where its instructions are

Part 2 has its own archive, with its own README, Docker environment and data
set. In the folder of this repository:

```bash
unzip CoreTrace-GUI_ATP_appendices.zip     # creates the appendices/ folder
```

Then open `appendices/README.md` and follow it: it gives what you need, the two
commands that start the application (`./build.sh`, then `./run.sh`, in
`appendices/docker`) and the address to open in your browser.

Three things to keep in mind while you read the Part 2 documents:

- They number the scenarios `F1` to `F24`. In the workbook the same scenarios
  are `GUI-F1` to `GUI-F24`: where they say `F9`, read `GUI-F9`.
- "The appendices ZIP" and `appendices/` mean the GUI archive and the folder it
  creates, not this repository and not the archive of the Innovation platform.
- Verdicts are `PASS` or `FAIL`, and anomalies go to
  <https://github.com/CoreTrace/coretrace-gui/issues>.

## For the CoreTrace team

### 6. Regenerating the workbook

The plan is generated, not hand-edited. Scenarios live in
`scripts/atp_scenarios.py`; the revisions under test are the `ARG *_REF` lines
of `docker/Dockerfile`.

```bash
python3 -m pip install openpyxl
python3 scripts/merge_gui_atp.py CoreTrace-GUI_ATP.xlsx ATP_CoreTrace.xlsx
python3 scripts/build_guide.py
```

`CoreTrace-GUI_ATP.xlsx` and `CoreTrace-GUI_ATP_appendices.zip` are the plan
and the archive delivered by the GUI team (`atp/` in `coretrace-gui`); the merge
script appends its rows to the two tabs under the keys `GUI-F<n>`, and adds to
the README of `CoreTrace-GUI_ATP_appendices.zip` a note that sends the reader
back to this file: copy the GUI team's archive here unchanged before each
merge. This README quotes the number of scenarios of each part: update it when
a count changes. The address of this repository is `ATP_REPO` in
`scripts/atp_scenarios.py`.
