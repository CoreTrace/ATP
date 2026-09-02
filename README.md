# CoreTrace — Acceptance Test Plan

Everything a tester needs to run the plan in `ATP_CoreTrace.xlsx` without help
from the CoreTrace team.

CoreTrace is a static and dynamic analysis toolchain for C/C++, made of four
repositories:

| Repository | What it does |
|---|---|
| `coretrace` | Orchestrator CLI and HTTP server; drives the analyzers and merges their reports. |
| `coretrace-stack-analyzer` | Static analysis on LLVM IR: stack usage, buffer overflows, pointer escapes, uninitialised reads. |
| `coretrace-concurrency-analyzer` | Static concurrency analysis: data races, missing joins, lock-order deadlocks. |
| `coretrace-runtime-analyzer` | Builds an instrumented binary, runs it, collects runtime events (bounds, allocations, vtables). |

There is no graphical interface and no account to create. The product is
evaluated through its command line, its reports (human / JSON / SARIF) and its
exit codes.

## 1. Get the sources

Clone the ATP repository together with its CoreTrace submodules:

```bash
git clone --recurse-submodules git@github.com:CoreTrace/ATP.git
```

If the ATP repository was cloned without `--recurse-submodules`, initialise
and check out all submodules afterwards:

```bash
git submodule update --init --recursive
```

The resulting layout — the *ATP root* every scenario is written against:

```
ATP/
├── ATP_CoreTrace.xlsx   the test plan
├── atp.sh               single entry point
├── docker/Dockerfile    Linux test image
├── datasets/            data referenced by the scenarios
├── coretrace/
├── coretrace-stack-analyzer/
├── coretrace-concurrency-analyzer/
└── coretrace-runtime-analyzer/
```

## 2. Choose a platform

The scenarios are identical on both. Only the setup differs.

### macOS (native)

```bash
brew install cmake ninja llvm@20 cppcheck
./atp.sh doctor         # names anything still missing
./atp.sh build-macos    # ~15 min
./atp.sh versions
```

### Linux (Docker)

```bash
./atp.sh build-linux    # ~30-60 min the first time, needs network access
./atp.sh linux          # shell inside the image, at /atp
```

The image is Ubuntu 24.04 with LLVM 20 and the four tools already built, so
nothing is compiled during testing. It runs unprivileged (uid 1000) on purpose:
several concurrency tests assert that an unreadable path fails, and root reads
it regardless.

Two scenarios (CORE-06, CORE-07) start a server and then query it. Open the
second terminal inside the *same* container:

```bash
docker ps                     # note the container id
docker exec -it <id> bash
```

## 3. Run the plan

Open `ATP_CoreTrace.xlsx`.

- **Info & Access** — environments, data sets, validation criteria, how to
  report an anomaly.
- **Test Plan** — 40 scenarios. Run them in order: `ENV-*` first, everything
  else depends on it.

Every command is written to be pasted from the ATP root (`/atp` in the
container) and each scenario begins with the `cd` it needs. Fill in
**Verdict** (OK / KO / Not run) and **Feedback** for each row.

A scenario is **OK** only if every element of *Expected result* is observed. If
anything differs, it is **KO** — write down what you saw, even partially.

## 4. Known defects

Some scenarios describe a defect that is already known. Mark them KO if you
hit it, quote the line, and do **not** open a new issue:

- **CORE-02 / CORE-04 / CORE-08** — two defects in the cppcheck integration.
  Its findings are never folded into the `(cppcheck) Diagnostics summary:`
  line, which always reads all zeros; and cppcheck is spawned through the
  hardcoded path `/opt/homebrew/bin/cppcheck`, so on Linux and on Intel macOS
  it never starts at all. CORE-08 (async proof) fails on Linux as a
  consequence.
- **RUN-05** — on macOS the instrumented binaries abort at process teardown
  (`libc++abi: mutex lock failed`), so batch mode reports
  `runtime_failures=3`. Event collection is unaffected. Linux reports
  `runtime_failures=0`.

## 5. Reporting

One GitHub issue per anomaly, in the repository named in the scenario's
**Component** column, titled with the scenario id — for example
`[STACK-05] index off by one not reported`. Include the platform, the exact
command, the full output, and the output of `./atp.sh versions`.

## 6. Regenerating the spreadsheet

The plan is generated, not hand-edited, so iterating between test cycles does
not disturb the layout:

```bash
python3 -m pip install openpyxl
python3 scripts/build_atp_xlsx.py
```

Scenarios live in `scripts/atp_scenarios.py` — adding or amending one is a data
edit.
