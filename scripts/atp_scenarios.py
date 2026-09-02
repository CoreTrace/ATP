# SPDX-License-Identifier: Apache-2.0
"""Scenario data for the CoreTrace Acceptance Test Plan.

Kept apart from the spreadsheet writer so that iterating on the plan between
test cycles is a data edit, not a formatting edit.

Every `steps` entry is a command a tester can paste verbatim from the ATP root
(the directory holding the four repositories on macOS, /atp in the Linux
image). Every `expected` entry is checkable without interpreting the tool's
intent: an exact counter, an exit code, a literal substring.
"""

CRITICAL = "Critical feature"
SECONDARY = "Secondary function"
INTERFACE = "User interface"

DONE = "Done"
IN_PROGRESS = "In progress"

BOTH = "macOS + Linux"

# Prerequisite fragments reused across scenarios, so a change to the setup
# contract does not have to be applied thirty times.
PRE_BUILT = (
    "ENV-01 (macOS) or ENV-02 (Linux) passed. All commands run from the ATP "
    "root: the folder containing the four repositories on macOS, /atp inside "
    "the Linux container."
)
PRE_PY = PRE_BUILT + " python3 >= 3.10 available."

SCENARIOS = [
    # ------------------------------------------------------------------ ENV
    dict(
        id="ENV-01",
        component="Environment",
        name="Native build of the four tools on macOS",
        category=CRITICAL,
        platform="macOS",
        status=DONE,
        objective=(
            "Obtain the four CoreTrace executables on macOS from a clean "
            "checkout, using a single command."
        ),
        prerequisites=(
            "macOS 14+ (Intel or Apple Silicon). Homebrew installed. "
            "The four repositories cloned side by side in the ATP root."
        ),
        steps=[
            "brew install cmake ninja llvm@20 cppcheck",
            "./atp.sh doctor",
            "./atp.sh build-macos",
            "./atp.sh versions",
        ],
        expected=(
            "`./atp.sh doctor` prints OK for cmake, ninja, git, python3, "
            "cppcheck and LLVM 20. `build-macos` ends without a CMake or "
            "compiler error. `versions` lists four lines and none of them "
            "says `not built`; the coretrace line starts with `ctrace v`."
        ),
    ),
    dict(
        id="ENV-02",
        component="Environment",
        name="Linux test image build (Docker)",
        category=CRITICAL,
        platform="Linux",
        status=DONE,
        objective=(
            "Obtain a reproducible Ubuntu 24.04 / LLVM 20 environment holding "
            "the four tools already built, so the Linux scenarios need no "
            "local toolchain."
        ),
        prerequisites=(
            "Docker Desktop or Docker Engine running, 25 GB free disk, "
            "network access (the image installs LLVM 20 and CMake fetches "
            "coretrace-compiler / coretrace-logger from GitHub). "
            "First build takes 30-60 min."
        ),
        steps=[
            "./atp.sh build-linux",
            "./atp.sh linux",
            "# inside the container:",
            "ls /atp",
            "/atp/coretrace/build/ctrace --version",
        ],
        expected=(
            "`docker build` ends with `naming to docker.io/library/"
            "coretrace-atp:latest`. Inside the container `ls /atp` lists the "
            "four repositories, the shell runs as uid 1000 (`ubuntu`), not "
            "root, and `ctrace --version` prints the same tag as on the host, "
            "e.g. `ctrace v0.74.0-12-g2fbd4a5`."
        ),
    ),

    # ---------------------------------------------------------------- STACK
    dict(
        id="STACK-01",
        component="coretrace-stack-analyzer",
        name="Static stack size and call-chain propagation",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that the analyzer reports the local frame size of each "
            "function and propagates the maximum through the call chain."
        ),
        prerequisites=PRE_PY,
        steps=[
            "cd coretrace-stack-analyzer",
            "./build/stack_usage_analyzer test/local-storage/c/stack-callee-caller.c --format=json > /tmp/stack01.json",
            "python3 -c \"import json;d=json.load(open('/tmp/stack01.json'));[print(f['name'],f['localStack'],f['maxStack']) for f in d['functions']]\"",
        ],
        expected=(
            "The JSON parses and prints one line per function. `foo` has a "
            "large `localStack` equal to its `maxStack` (it calls nothing). "
            "`bar` and `mano` have `localStack` 0 but the same `maxStack` as "
            "`foo` — the callee frame was propagated up the call chain, which "
            "is the point of the check. A `maxStack` equal to `localStack` on "
            "every function would be a failure."
        ),
    ),
    dict(
        id="STACK-02",
        component="coretrace-stack-analyzer",
        name="Dynamic stack usage (VLA / alloca) and unknown propagation",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that a runtime-sized allocation is flagged as dynamic and "
            "that the resulting stack size is reported as unknown rather than "
            "silently understated."
        ),
        prerequisites=PRE_PY,
        steps=[
            "cd coretrace-stack-analyzer",
            "./build/stack_usage_analyzer test/vla/vla-scanf.c --format=json > /tmp/stack02.json",
            "python3 -c \"import json;d=json.load(open('/tmp/stack02.json'));[print(f['name'],f['hasDynamicAlloca'],f['maxStackUnknown']) for f in d['functions']]\"",
            "./build/stack_usage_analyzer test/vla/vla-scanf.c --warnings-only",
        ],
        expected=(
            "For function `main`: `hasDynamicAlloca` is true and "
            "`maxStackUnknown` is true. The human output contains "
            "`allocation performed via alloca/VLA` and "
            "`size is unbounded at compile time`."
        ),
    ),
    dict(
        id="STACK-03",
        component="coretrace-stack-analyzer",
        name="Infinite recursion detection",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that unconditional self recursion is reported as an error, "
            "and that bounded recursion is not."
        ),
        prerequisites=PRE_BUILT,
        steps=[
            "cd coretrace-stack-analyzer",
            "./build/stack_usage_analyzer test/recursion/c/infinite-recursion.c --warnings-only",
            "./build/stack_usage_analyzer test/recursion/c/limited-recursion.c --warnings-only",
        ],
        expected=(
            "First run: `[!!!Error] unconditional self recursion detected "
            "(no base case)` and `Diagnostics summary: info=0, warning=0, "
            "error=1`. Second run: `Diagnostics summary: info=0, warning=0, "
            "error=0` — no diagnostic on the bounded case."
        ),
    ),
    dict(
        id="STACK-04",
        component="coretrace-stack-analyzer",
        name="Stack pointer escape detection",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that the address of a local returned to the caller is "
            "reported, with the escape route named."
        ),
        prerequisites=PRE_BUILT,
        steps=[
            "cd coretrace-stack-analyzer",
            "./build/stack_usage_analyzer test/security/stack-escape/11_return_local.c --warnings-only",
        ],
        expected=(
            "Output contains `stack pointer escape: address of variable 'x' "
            "escapes this function` and the note `escape via return statement "
            "(pointer to stack returned to caller)`."
        ),
    ),
    dict(
        id="STACK-05",
        component="coretrace-stack-analyzer",
        name="Static stack-buffer overflow detection (F10)",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that an out-of-bounds write on a stack array is reported "
            "with the variable name, its size and the offending index."
        ),
        prerequisites=PRE_PY,
        steps=[
            "cd coretrace-stack-analyzer",
            "./build/stack_usage_analyzer test/security/buffer-overflow/01_buffer_overflow.c --warnings-only",
            "python3 -B BTP-STACK-ANALYZER-F10.py",
        ],
        expected=(
            "The analyzer reports, in `vuln_off_by_one`, `potential stack "
            "buffer overflow on variable 'buf' (size 10)` with the note "
            "`index variable may go up to 10 (array last valid index: 9)`, and "
            "`Diagnostics summary: info=0, warning=4, error=0`. The F10 proof "
            "script ends with a green `PASS` line and exits 0."
        ),
    ),
    dict(
        id="STACK-06",
        component="coretrace-stack-analyzer",
        name="Memory intrinsic overflow and aliasing (F2)",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that memcpy/memset writes larger than the destination "
            "stack buffer are reported, including through pointer aliases."
        ),
        prerequisites=PRE_PY,
        steps=[
            "cd coretrace-stack-analyzer",
            "./build/stack_usage_analyzer test/cpy-buffer/bad-usage-memcpy.c --warnings-only",
            "python3 -B BTP-STACK-ANALYZER-F2.py",
        ],
        expected=(
            "The first command reports `potential stack buffer overflow in "
            "memcpy on variable 'buf'` with "
            "`destination stack buffer size: 10 bytes` and "
            "`requested 20 bytes to be copied/initialized`. The F2 proof "
            "covers memcpy, memset, deep aliasing and const-correctness and "
            "ends with `PASS`, exit 0."
        ),
    ),
    dict(
        id="STACK-07",
        component="coretrace-stack-analyzer",
        name="Configurable stack limit",
        category=SECONDARY,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that the stack budget is configurable and that the "
            "reported limit follows the option."
        ),
        prerequisites=PRE_BUILT,
        steps=[
            "cd coretrace-stack-analyzer",
            "./build/stack_usage_analyzer test/local-storage/c/stack-exhaustion-large-frame.c --warnings-only",
            "./build/stack_usage_analyzer test/local-storage/c/stack-exhaustion-large-frame.c --stack-limit=64KiB --warnings-only",
        ],
        expected=(
            "Both runs report `[!!!Error] potential stack overflow: exceeds "
            "limit of ...`. The first names `8388608 bytes` (8 MiB default), "
            "the second `65536 bytes`, showing the option was applied."
        ),
    ),
    dict(
        id="STACK-08",
        component="coretrace-stack-analyzer",
        name="Human, JSON and SARIF reporting (F5)",
        category=INTERFACE,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that the same analysis is available in a readable CLI "
            "form, a machine-readable JSON form and a SARIF form consumable "
            "by GitHub code scanning, with consistent counts."
        ),
        prerequisites=PRE_PY,
        steps=[
            "cd coretrace-stack-analyzer",
            "./build/stack_usage_analyzer test/security/buffer-overflow/01_buffer_overflow.c --warnings-only",
            "./build/stack_usage_analyzer test/security/buffer-overflow/01_buffer_overflow.c --format=json | python3 -m json.tool > /dev/null && echo JSON_OK",
            "./build/stack_usage_analyzer test/security/buffer-overflow/01_buffer_overflow.c --format=sarif > /tmp/stack08.sarif",
            "python3 -c \"import json;d=json.load(open('/tmp/stack08.sarif'));print(d['runs'][0]['tool']['driver']['name'],len(d['runs'][0]['results']))\"",
            "python3 -B BTP-STACK-ANALYZER-F5.py",
        ],
        expected=(
            "`JSON_OK` is printed. The SARIF line prints "
            "`coretrace-stack-analyzer 5`. The F5 proof runs the three "
            "formats over three fixtures, confirms diagnostic counts match "
            "across formats, and ends with `PASS`, exit 0."
        ),
    ),
    dict(
        id="STACK-09",
        component="coretrace-stack-analyzer",
        name="Itanium ABI mangling and demangling (F8)",
        category=SECONDARY,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that C++ symbols are shown both raw and demangled with "
            "their parameter list, and that JSON keeps the raw IR symbol for "
            "tooling."
        ),
        prerequisites=PRE_PY,
        steps=[
            "cd coretrace-stack-analyzer",
            "./build/stack_usage_analyzer test/test.cpp | head -5",
            "./build/stack_usage_analyzer test/test.cpp --demangle | head -5",
            "./build/stack_usage_analyzer test/test.cpp --format=json | python3 -c \"import sys,json;print(json.load(sys.stdin)['functions'][0]['name'])\"",
            "python3 -B BTP-STACK-ANALYZER-F8.py",
        ],
        expected=(
            "Default human output shows both forms on one line, e.g. "
            "`_ZN12demo_symbols17scalar_parametersEidc "
            "demo_symbols::scalar_parameters(int, double, char)`. With "
            "`--demangle` only the readable signature remains. JSON prints "
            "the raw symbol `_ZN12demo_symbols17scalar_parametersEidc`. The "
            "F8 proof ends with `PASS`, exit 0."
        ),
    ),
    dict(
        id="STACK-10",
        component="coretrace-stack-analyzer",
        name="Clean source produces no diagnostic",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that a correct program is not flagged — the baseline "
            "false-positive check."
        ),
        prerequisites=PRE_BUILT,
        steps=[
            "cd coretrace-stack-analyzer",
            "./build/stack_usage_analyzer test/no-error/basic-main.c --warnings-only",
        ],
        expected=(
            "Output is exactly `Mode: IR` followed by "
            "`Diagnostics summary: info=0, warning=0, error=0`. No warning, "
            "no error, exit code 0."
        ),
    ),
    dict(
        id="STACK-11",
        component="coretrace-stack-analyzer",
        name="False-positive regression corpus",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that the patterns that used to produce false positives "
            "(wrapper allocators, merged returns, vendor headers, Vulkan-style "
            "out-parameters) are still silent."
        ),
        prerequisites=PRE_BUILT + " Shell is bash or zsh. The datasets/ folder of\n            the ATP appendix sits next to the repositories.",
        steps=[
            "cd coretrace-stack-analyzer",
            "grep -v '^#' ../datasets/stack-no-false-positive.txt | grep -v '^$' | "
            "while read f; do n=$(./build/stack_usage_analyzer \"$f\" --warnings-only "
            "2>/dev/null | grep -c '!!'); echo \"$n $f\"; done",
        ],
        expected=(
            "15 lines, every one starting with `0`. Any line starting with a "
            "non-zero count is a false-positive regression: report the file "
            "name in Feedback. (The rest of test/false-positive-repro/ is not "
            "checked here: those fixtures reproduce one false positive while "
            "still containing a real defect, so they legitimately emit "
            "diagnostics. STACK-12 checks them against the expectations "
            "embedded in each file.)"
        ),
    ),
    dict(
        id="STACK-12",
        component="coretrace-stack-analyzer",
        name="Full regression suite, including the SMT pass",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Run the whole fixture suite twice — once with the default "
            "engine, once with SMT refinement on the z3 backend — and check "
            "that both agree with the expectations embedded in the fixtures."
        ),
        prerequisites=PRE_PY + " Takes 5-20 min depending on the machine.",
        steps=[
            "cd coretrace-stack-analyzer",
            "python3 -u run_test.py --jobs 8",
        ],
        expected=(
            "The run ends with `All tests passed.` and "
            "`Passed N/N tests.` with no failure — 1711/1711 as of "
            "coretrace-stack-analyzer v0.19.0. Exit code 0. The report "
            "includes `(smt-z3)` lines, proving the SMT pass ran and did not "
            "change the verdicts."
        ),
    ),
    dict(
        id="STACK-13",
        component="coretrace-stack-analyzer",
        name="CI adapter: artifacts and policy gate",
        category=SECONDARY,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that the CI wrapper exports JSON and SARIF artifacts and "
            "fails the build only when the configured severity is reached."
        ),
        prerequisites=PRE_PY,
        steps=[
            "cd coretrace-stack-analyzer",
            "mkdir -p /tmp/atp-artifacts",
            "python3 scripts/ci/run_code_analysis.py --analyzer ./build/stack_usage_analyzer "
            "--fail-on error --json-out /tmp/atp-artifacts/bad.json "
            "--sarif-out /tmp/atp-artifacts/bad.sarif "
            "test/local-storage/c/stack-exhaustion-large-frame.c; echo \"exit=$?\"",
            "python3 scripts/ci/run_code_analysis.py --analyzer ./build/stack_usage_analyzer "
            "--fail-on error --json-out /tmp/atp-artifacts/ok.json "
            "--sarif-out /tmp/atp-artifacts/ok.sarif "
            "test/no-error/basic-main.c; echo \"exit=$?\"",
        ],
        expected=(
            "First run prints `Findings summary: errors=1, warnings=1, "
            "infos=0`, then `CI gate failed (fail-on=error).` and `exit=1`. "
            "Second run prints `exit=0`. All four artifact files exist and "
            "the two .sarif files parse as JSON."
        ),
    ),
    dict(
        id="STACK-14",
        component="coretrace-stack-analyzer",
        name="Error handling on invalid input",
        category=SECONDARY,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that a missing file and an unknown option are refused "
            "with a readable message instead of a crash."
        ),
        prerequisites=PRE_BUILT,
        steps=[
            "cd coretrace-stack-analyzer",
            "./build/stack_usage_analyzer /tmp/does-not-exist.c; echo \"exit=$?\"",
            "./build/stack_usage_analyzer --not-a-real-option test/no-error/basic-main.c; echo \"exit=$?\"",
            "./build/stack_usage_analyzer --help | head -3",
        ],
        expected=(
            "The missing file prints `Compilation failed:` followed by "
            "`error reading '/tmp/does-not-exist.c': No such file or "
            "directory` and `Failed to analyze: ...`, then `exit=1`. The bad "
            "option prints `Unknown option: --not-a-real-option`, then "
            "`exit=1`. Neither segfaults, prints a stack trace or hangs. "
            "`--help` prints the banner `Stack Usage Analyzer - static stack "
            "usage analysis for LLVM IR/bitcode`."
        ),
    ),

    # ----------------------------------------------------------------- CONC
    dict(
        id="CONC-01",
        component="coretrace-concurrency-analyzer",
        name="Data race on an unsynchronised global",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that concurrent unprotected access to a shared global is "
            "reported as an error, with both conflicting accesses located."
        ),
        prerequisites=PRE_BUILT,
        steps=[
            "cd coretrace-concurrency-analyzer",
            "./build/coretrace_concurrency_analyzer "
            "tests/fixtures/concurrency/data-race/data_race_basic.c --analyze --format=human",
        ],
        expected=(
            "One diagnostic with `severity: ERROR`, `ruleId: DataRaceGlobal`, "
            "`cwe: CWE-362`, `symbol: shared_counter`, the message "
            "`unsynchronized concurrent access to global 'shared_counter'`, a "
            "`first access` and a `conflicting access` note each carrying "
            "file:line:column, and `Diagnostics summary: info=0, warning=0, "
            "error=1`."
        ),
    ),
    dict(
        id="CONC-02",
        component="coretrace-concurrency-analyzer",
        name="Thread handle never joined or detached",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that a joinable thread leaving scope without join or "
            "detach is reported, for both pthread and std::thread."
        ),
        prerequisites=PRE_BUILT,
        steps=[
            "cd coretrace-concurrency-analyzer",
            "./build/coretrace_concurrency_analyzer "
            "tests/fixtures/concurrency/missing-join/missing_join_basic.c --analyze --rules=missing-join",
            "./build/coretrace_concurrency_analyzer "
            "tests/fixtures/concurrency/missing-join/cpp_std_thread_missing_join.cpp --analyze --rules=missing-join",
            "./build/coretrace_concurrency_analyzer "
            "tests/fixtures/concurrency/missing-join/pthread_join_all_no_missing_join.c --analyze --rules=missing-join",
        ],
        expected=(
            "The first two runs report `ruleId: MissingJoin` with "
            "`thread handle is not joined or detached before scope exit`; the "
            "pthread case shows `handle kind: pthread` and "
            "`lifecycle summary: creates=1, joins=0, detaches=0`. The third "
            "run, where every thread is joined, reports "
            "`info=0, warning=0, error=0`."
        ),
    ),
    dict(
        id="CONC-03",
        component="coretrace-concurrency-analyzer",
        name="Deadlock through lock-order inversion",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that two threads taking the same two mutexes in opposite "
            "order are reported, with both orders shown."
        ),
        prerequisites=PRE_BUILT,
        steps=[
            "cd coretrace-concurrency-analyzer",
            "./build/coretrace_concurrency_analyzer "
            "tests/fixtures/concurrency/deadlock/deadlock_basic.c --analyze --rules=deadlock-lock-order",
        ],
        expected=(
            "`severity: ERROR`, `ruleId: DeadlockLockOrder`, `cwe: CWE-833`, "
            "message `potential deadlock caused by inconsistent lock "
            "acquisition order`, a `first order: acquire 'lockB' while holding "
            "'lockA'` note and a `conflicting order: acquire 'lockA' while "
            "holding 'lockB'` note, and `error=1`."
        ),
    ),
    dict(
        id="CONC-04",
        component="coretrace-concurrency-analyzer",
        name="Deadlock through a three-lock cycle",
        category=SECONDARY,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that a cycle spanning three mutexes across three functions "
            "is detected, not only the two-lock case."
        ),
        prerequisites=PRE_BUILT,
        steps=[
            "cd coretrace-concurrency-analyzer",
            "./build/coretrace_concurrency_analyzer "
            "tests/fixtures/concurrency/deadlock/deadlock_three_lock_cycle.c --analyze --rules=deadlock-lock-order",
        ],
        expected=(
            "One error reading `potential deadlock caused by a cycle of 3 "
            "lock acquisitions`, listing the three edges "
            "first_lock->second_lock, second_lock->third_lock and "
            "third_lock->first_lock, and `error=1`."
        ),
    ),
    dict(
        id="CONC-05",
        component="coretrace-concurrency-analyzer",
        name="No false positive on correctly synchronised code",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that code protected by lock_guard, atomics, a condition "
            "variable or C++20 jthread auto-join produces no diagnostic."
        ),
        prerequisites=PRE_BUILT + " Shell is bash or zsh.",
        steps=[
            "cd coretrace-concurrency-analyzer",
            "n=0; bad=0; for f in tests/fixtures/concurrency/*/*_no_fp.* "
            "tests/fixtures/concurrency/*/*_no_diagnostic.* "
            "tests/fixtures/concurrency/*/*_no_missing_join.*; do n=$((n+1)); "
            "s=$(./build/coretrace_concurrency_analyzer \"$f\" --analyze 2>/dev/null | tail -1); "
            "case \"$s\" in *error=0*) ;; *) bad=$((bad+1)); echo \"BAD $s | $f\";; esac; "
            "done; echo \"checked=$n bad=$bad\"",
            "./build/coretrace_concurrency_analyzer "
            "tests/fixtures/concurrency-cxx20/cpp_jthread_auto_join_no_missing_join.cpp "
            "--analyze -- -std=c++20 | tail -1",
        ],
        expected=(
            "The loop prints `checked=28 bad=0` and no `BAD` line. Each `BAD` "
            "line is a false positive: report the file name in Feedback. The "
            "C++20 jthread case prints `Diagnostics summary: info=0, "
            "warning=0, error=0` — a jthread joins in its destructor, so it "
            "must not be reported as a missing join. (The `-- -std=c++20` "
            "suffix is required: without it clang defaults to an older "
            "standard and the fixture fails to compile.)"
        ),
    ),
    dict(
        id="CONC-06",
        component="coretrace-concurrency-analyzer",
        name="Rule selection",
        category=SECONDARY,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that --rules restricts the analysis to the requested "
            "checkers."
        ),
        prerequisites=PRE_BUILT,
        steps=[
            "cd coretrace-concurrency-analyzer",
            "./build/coretrace_concurrency_analyzer "
            "tests/fixtures/concurrency/deadlock/deadlock_basic.c --analyze --rules=data-race | tail -1",
            "./build/coretrace_concurrency_analyzer "
            "tests/fixtures/concurrency/deadlock/deadlock_basic.c --analyze --rules=deadlock-lock-order | tail -1",
        ],
        expected=(
            "With `--rules=data-race` the deadlock fixture reports "
            "`info=0, warning=0, error=0` — the deadlock checker did not run. "
            "With `--rules=deadlock-lock-order` the same file reports "
            "`error=1`."
        ),
    ),
    dict(
        id="CONC-07",
        component="coretrace-concurrency-analyzer",
        name="Human, JSON and SARIF reporting",
        category=INTERFACE,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that concurrency diagnostics are available in the three "
            "output formats with the same content."
        ),
        prerequisites=PRE_PY,
        steps=[
            "cd coretrace-concurrency-analyzer",
            "F=tests/fixtures/concurrency/data-race/data_race_basic.c",
            "./build/coretrace_concurrency_analyzer $F --analyze --format=json | python3 -m json.tool > /dev/null && echo JSON_OK",
            "./build/coretrace_concurrency_analyzer $F --analyze --format=sarif > /tmp/conc07.sarif",
            "python3 -c \"import json;d=json.load(open('/tmp/conc07.sarif'));r=d['runs'][0];print(r['tool']['driver']['name'],len(r['results']),r['results'][0]['ruleId'])\"",
        ],
        expected=(
            "`JSON_OK` is printed. The last command prints "
            "`coretrace-concurrency-analyzer 1 DataRaceGlobal`. The JSON "
            "diagnostic carries `cwe`, `confidence`, `notes` and "
            "`properties` fields."
        ),
    ),
    dict(
        id="CONC-08",
        component="coretrace-concurrency-analyzer",
        name="Unit, architecture and golden-output test suites",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Run the repository's own suites: CTest for the C++ unit and "
            "architecture tests, pytest for the fixture-embedded expected "
            "human output."
        ),
        prerequisites=(
            PRE_PY + " pytest available. It is already installed in the Linux "
            "image, so inside the container skip step 2 and call `python3 -m "
            "pytest` directly. On macOS, Homebrew's Python refuses `pip "
            "install` (PEP 668), hence the virtualenv in step 2."
        ),
        steps=[
            "python3 -m venv .venv-atp && ./.venv-atp/bin/pip install pytest   # macOS only, once",
            "cd coretrace-concurrency-analyzer",
            "ctest --test-dir build --output-on-failure",
            "CORETRACE_ANALYZER_BIN=./build/coretrace_concurrency_analyzer "
            "../.venv-atp/bin/python -m pytest tests/integration/cli/test_human_output_golden.py -q",
        ],
        expected=(
            "CTest prints `100% tests passed, 0 tests failed out of N` — N "
            "is 4 without pytest on the host, 5 with it (the golden suite is "
            "registered only when CMake finds Python3), and is 5 in the Linux "
            "image. pytest prints `4 passed`; each fixture's actual human "
            "output matches its embedded EXPECT-HUMAN-DIAGNOSTICS block. "
            "Do NOT run the whole `tests/integration/cli` directory: "
            "`test_analyzer.py` needs the separate coretrace-testkit package "
            "and will error on collection."
        ),
    ),
    dict(
        id="CONC-09",
        component="coretrace-concurrency-analyzer",
        name="Error handling on invalid input",
        category=SECONDARY,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that a missing file and a syntactically invalid source are "
            "reported as structured errors with a non-zero exit code."
        ),
        prerequisites=PRE_BUILT,
        steps=[
            "cd coretrace-concurrency-analyzer",
            "./build/coretrace_concurrency_analyzer /tmp/does-not-exist.c --analyze; echo \"exit=$?\"",
            "./build/coretrace_concurrency_analyzer tests/fixtures/invalid.c --analyze; echo \"exit=$?\"",
        ],
        expected=(
            "The missing file yields `ruleId: CompilerDiagnostic` and the "
            "note `validate_input: input_file_does_not_exist: input file does "
            "not exist (/tmp/does-not-exist.c)`, then `exit=1`. The invalid "
            "source yields the clang parse errors and `exit=1`. Neither run "
            "crashes."
        ),
    ),

    # ------------------------------------------------------------------ RUN
    dict(
        id="RUN-01",
        component="coretrace-runtime-analyzer",
        name="Instrumented build, execution and event collection (F4)",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check the minimal end-to-end path: compile a source with "
            "instrumentation, run the binary, capture its output and count "
            "the CoreTrace events."
        ),
        prerequisites=PRE_PY,
        steps=[
            "cd coretrace-runtime-analyzer",
            "python3 -B BTP-RUNTIME-ANALYZER_F4.py",
        ],
        expected=(
            "The script reports `binary_generated=OK`, "
            "`binary_executable=OK`, `coretrace_lines_collected=OK`, "
            "`entry_events_collected=OK`, `exit_events_collected=OK`, then "
            "`[F4] result=OK`, exit 0. The collection block shows "
            "`entry_events=2` and `exit_events=2`."
        ),
    ),
    dict(
        id="RUN-02",
        component="coretrace-runtime-analyzer",
        name="Heap buffer overflow detected at runtime (F11)",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that bounds instrumentation catches an out-of-bounds write "
            "while the program runs, reports the access site and the "
            "allocation site, and lets the program continue."
        ),
        prerequisites=PRE_PY,
        steps=[
            "cd coretrace-runtime-analyzer",
            "python3 -B BTP-RUNTIME-ANALYZER_F11.py --no-color",
        ],
        expected=(
            "Output contains `ct: heap-buffer-overflow WRITE of size 1` with "
            "an `access=...:18:15` line, an `alloc_site=...:6:63` line and "
            "`alloc_size=8`. Status lines "
            "`heap_buffer_overflow_reported=OK`, `write_overflow_reported=OK`, "
            "`bounds_errors_collected=OK`, `program_continued_after_detection"
            "=OK`, then a final `PASS`, exit 0."
        ),
    ),
    dict(
        id="RUN-03",
        component="coretrace-runtime-analyzer",
        name="Allocation lifecycle tracing",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that malloc, realloc and free are traced with sizes and "
            "call sites, and that an allocation with no surviving reference "
            "is flagged as unreachable."
        ),
        prerequisites=PRE_BUILT,
        steps=[
            "cd coretrace-runtime-analyzer",
            "./build/runtime-analyzer -o /tmp/atp-alloc --show-events -- test/ct_alloc_basic.c",
        ],
        expected=(
            "The event stream shows `tracing-malloc` with a "
            "`site=ct_alloc_basic.c:...` reference, a `tracing-realloc` block "
            "with `status : moved` plus old/new sizes, a `tracing-free`, and a "
            "`tracing-malloc-unreachable` block with `status : unreachable`. "
            "The summary reports `allocation_events` >= 6 (6 on macOS, 8 on "
            "Linux — the count depends on the platform allocator, only the "
            "presence of the four event kinds is contractual)."
        ),
    ),
    dict(
        id="RUN-04",
        component="coretrace-runtime-analyzer",
        name="Virtual dispatch (vtable) tracing",
        category=SECONDARY,
        platform=BOTH,
        status=IN_PROGRESS,
        objective=(
            "Check that virtual calls are traced with the this pointer, the "
            "vtable pointer and the resolved dynamic type, and that a call on "
            "a freed object shows the type as unknown."
        ),
        prerequisites=PRE_BUILT,
        steps=[
            "cd coretrace-runtime-analyzer",
            "./build/runtime-analyzer -o /tmp/atp-vt --show-events -- --ct-modules=all test/ct_vtable_diag_freed.cpp",
        ],
        expected=(
            "Two `[VTABLE]` blocks. The first, on the live object, shows "
            "`type    : Derived` with a non-null `vtable` address. The second, "
            "after the object is freed, shows `type : <unknown>` for the same "
            "`this` pointer — the signature of a use-after-free virtual call."
        ),
    ),
    dict(
        id="RUN-05",
        component="coretrace-runtime-analyzer",
        name="Batch mode over a test directory",
        category=SECONDARY,
        platform=BOTH,
        status=IN_PROGRESS,
        objective=(
            "Check that every source under a directory is compiled and run as "
            "its own instrumented binary, and that per-file results are "
            "aggregated instead of the run stopping at the first failure."
        ),
        prerequisites=PRE_BUILT + " Takes several minutes.",
        steps=[
            "cd coretrace-runtime-analyzer",
            "mkdir -p /tmp/atp-rt-src && cp test/ct_alloc_basic.c test/ct_autofree_local.c "
            "test/ct_new_delete.cpp /tmp/atp-rt-src/",
            "./build/runtime-analyzer --test-dir /tmp/atp-rt-src --output-dir /tmp/atp-rt-out",
        ],
        expected=(
            "The batch block reports `tests=3` and `compile_failures=0`, and "
            "one `[RUNTIME]` line per source naming the generated binary. "
            "KNOWN LIMITATION (macOS only, open issue): the instrumented "
            "binaries abort at process teardown with `libc++abi: mutex lock "
            "failed`, so `runtime_failures=3` and `exit_code=134`. Collection "
            "is unaffected. On Linux the same command reports "
            "`runtime_failures=0`. Report only deviations from this."
        ),
    ),

    # ----------------------------------------------------------------- CORE
    dict(
        id="CORE-01",
        component="coretrace",
        name="CLI help and version",
        category=INTERFACE,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that the orchestrator documents its options and reports a "
            "version traceable to a git tag."
        ),
        prerequisites=PRE_BUILT,
        steps=[
            "cd coretrace",
            "./build/ctrace --help",
            "./build/ctrace --version",
        ],
        expected=(
            "`--help` lists at least `--static`, `--dyn`, `--invoke`, "
            "`--input`, `--sarif-format`, `--config`, `--ipc` and `--async`, "
            "and ends with an Examples section. `--version` prints "
            "`ctrace v<tag>`, e.g. `ctrace v0.74.0-12-g2fbd4a5`."
        ),
    ),
    dict(
        id="CORE-02",
        component="coretrace",
        name="Full static analysis pipeline",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that `--static` runs the whole static suite over a file "
            "and prints a per-tool diagnostics summary."
        ),
        prerequisites=PRE_BUILT + " cppcheck installed and on PATH.",
        steps=[
            "cd coretrace",
            "./build/ctrace --input tests/null_pointer.c --static",
        ],
        expected=(
            "One `Diagnostics summary: info=..., warning=..., error=...` line "
            "per tool, prefixed with the tool name in parentheses. The "
            "`(ctrace_stack_analyzer)` line reports `error=1` and the analyzer "
            "output above it contains `potential null pointer dereference`. "
            "Exit code 0. NOTE: tools not compiled into this build "
            "(flawfinder, tscancode, ikos — optional CMake features, OFF by "
            "default) report `info=0, warning=0, error=0`; that is expected, "
            "not a failure. The `(cppcheck)` line also reports all zeros on "
            "both platforms — see the two defects documented in CORE-04 — so "
            "`(ctrace_stack_analyzer)` is the only line carrying a meaningful "
            "count today."
        ),
    ),
    dict(
        id="CORE-03",
        component="coretrace",
        name="Selective tool invocation",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that `--invoke` runs only the named analyzers, so a user "
            "can pay for the checks they want."
        ),
        prerequisites=PRE_BUILT + " cppcheck installed and on PATH.",
        steps=[
            "cd coretrace",
            "./build/ctrace --input tests/null_pointer.c --invoke ctrace_stack_analyzer",
            "./build/ctrace --input tests/null_pointer.c --invoke cppcheck",
        ],
        expected=(
            "The first run prints one summary line, "
            "`(ctrace_stack_analyzer) ... error=1`, and no cppcheck output. "
            "The second prints only `(cppcheck) ...`. Both exit 0. KNOWN "
            "COSMETIC DEFECT (open issue): the progress line always reads "
            "`Running ikos on <file>` regardless of the tool actually being "
            "run; the tool that executes is the one named in the summary."
        ),
    ),
    dict(
        id="CORE-04",
        component="coretrace",
        name="Third-party analyzer integration (cppcheck)",
        category=CRITICAL,
        platform="macOS (Apple Silicon) only — see expected result",
        status=IN_PROGRESS,
        objective=(
            "Check that an external analyzer is driven by CoreTrace and that "
            "its findings are normalised into the CoreTrace summary."
        ),
        prerequisites=PRE_BUILT + " cppcheck installed and on PATH (`cppcheck --version`).",
        steps=[
            "cd coretrace",
            "cppcheck --version",
            "cppcheck tests/null_pointer.c",
            "./build/ctrace --input tests/null_pointer.c --invoke cppcheck --verbose",
        ],
        expected=(
            "On Apple Silicon macOS: cppcheck's own findings are printed "
            "through, with file:line:column — `tests/null_pointer.c:8:6: "
            "error: Null pointer dereference: ptr [nullPointer]` and "
            "`:21:6: warning: ... [nullPointerOutOfMemory]`. Exit code 0. "
            "TWO KNOWN DEFECTS, both open issues, both in "
            "CppCheckToolImplementation "
            "(include/Process/Tools/AnalysisTools.hpp). "
            "(1) Not normalised: the `(cppcheck) Diagnostics summary:` line "
            "always reads `info=0, warning=0, error=0`, even though cppcheck "
            "just reported one error and one warning — its findings never "
            "reach the CoreTrace summary, so a CI gate built on that summary "
            "would miss them. "
            "(2) Not portable: the tool spawns the hardcoded path "
            "/opt/homebrew/bin/cppcheck instead of resolving cppcheck from "
            "PATH, so on Linux — and on Intel macOS, where Homebrew lives in "
            "/usr/local — the process never starts and no finding is printed "
            "at all; the run still prints `Creating Linux process for "
            "command: /opt/homebrew/bin/cppcheck`, while cppcheck invoked "
            "directly at step 3 does find the dereference. "
            "Testers: mark this scenario KO, quote what you saw, and do not "
            "open a new anomaly for either defect."
        ),
    ),
    dict(
        id="CORE-05",
        component="coretrace",
        name="SARIF report file",
        category=INTERFACE,
        platform=BOTH,
        status=IN_PROGRESS,
        objective=(
            "Check that CoreTrace can write a valid SARIF report to a chosen "
            "path, for consumption by GitHub code scanning."
        ),
        prerequisites=PRE_PY,
        steps=[
            "cd coretrace",
            "python3 -c \"import json;c=json.load(open('config/tool-config.json'));"
            "c['stack_analyzer']['output_format']='sarif';"
            "c['analysis']['invoke']=['ctrace_stack_analyzer'];"
            "json.dump(c,open('config/atp-sarif.json','w'),indent=2)\"",
            "./build/ctrace --config config/atp-sarif.json --input tests/null_pointer.c "
            "--report-file /tmp/atp-core.sarif",
            "python3 -c \"import json;d=json.load(open('/tmp/atp-core.sarif'));"
            "print(d['runs'][0]['tool']['driver']['name'],len(d['runs'][0]['results']))\"",
            "rm -f config/atp-sarif.json",
        ],
        expected=(
            "The last command prints `coretrace-stack-analyzer 1` and the "
            "file has the SARIF top-level keys `version`, `$schema`, `runs`. "
            "KNOWN GAP (open issue): the `--sarif-format` CLI flag currently "
            "only affects the cppcheck/tscancode/flawfinder wrappers; the "
            "stack analyzer's format is set through "
            "`stack_analyzer.output_format` in the config file, which is what "
            "this scenario uses. The config must live in `config/` because "
            "model paths inside it are resolved relative to it."
        ),
    ),
    dict(
        id="CORE-06",
        component="coretrace",
        name="HTTP server mode",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that CoreTrace can serve analyses over HTTP so a UI or a "
            "CI runner can drive it without spawning a process per request."
        ),
        prerequisites=PRE_BUILT + " curl available. TCP port 8099 free. "
                                  "In the Linux image, run both commands in the same container "
                                  "(second terminal: `docker exec -it <id> bash`).",
        steps=[
            "cd coretrace",
            "./build/ctrace --ipc serve --serve-host 127.0.0.1 --serve-port 8099 "
            "--shutdown-token atp-secret &",
            "sleep 2",
            "curl -s -X POST http://127.0.0.1:8099/api -H 'Content-Type: application/json' "
            "-d '{\"proto\":\"coretrace-1.0\",\"id\":1,\"type\":\"request\","
            "\"method\":\"run_analysis\",\"params\":{\"input\":[\"./tests/null_pointer.c\"],"
            "\"invoke\":[\"ctrace_stack_analyzer\"],\"static_analysis\":false,"
            "\"dynamic_analysis\":false,\"async\":false}}'",
            "curl -s -o /dev/null -w '%{http_code}\\n' -X POST http://127.0.0.1:8099/shutdown "
            "-H 'Authorization: Bearer atp-secret'",
        ],
        expected=(
            "The /api call returns JSON with `\"status\":\"ok\"`, "
            "`\"proto\":\"coretrace-1.0\"`, `\"id\":1`, an "
            "`\"invoked_tools\":[\"ctrace_stack_analyzer\"]` field and a "
            "`\"diagnostics_summary_total\"` object. The shutdown call prints "
            "`202` and the background server exits."
        ),
    ),
    dict(
        id="CORE-07",
        component="coretrace",
        name="Server shutdown is token-protected",
        category=CRITICAL,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that the shutdown endpoint cannot be triggered without the "
            "configured token — an unauthenticated shutdown would be a denial "
            "of service on a shared analysis server."
        ),
        prerequisites=PRE_BUILT + " curl available. TCP port 8098 free.",
        steps=[
            "cd coretrace",
            "./build/ctrace --ipc serve --serve-host 127.0.0.1 --serve-port 8098 "
            "--shutdown-token atp-secret &",
            "sleep 2",
            "curl -s -o /dev/null -w 'no-token=%{http_code}\\n' -X POST http://127.0.0.1:8098/shutdown",
            "curl -s -o /dev/null -w 'wrong-token=%{http_code}\\n' -X POST "
            "http://127.0.0.1:8098/shutdown -H 'Authorization: Bearer wrong'",
            "curl -s -o /dev/null -w 'good-token=%{http_code}\\n' -X POST "
            "http://127.0.0.1:8098/shutdown -H 'Authorization: Bearer atp-secret'",
        ],
        expected=(
            "`no-token=403`, `wrong-token=403`, `good-token=202`. The server "
            "is still serving after the two rejected calls and stops only "
            "after the third."
        ),
    ),
    dict(
        id="CORE-08",
        component="coretrace",
        name="Asynchronous execution keeps results complete (F7)",
        category=CRITICAL,
        platform="macOS (Apple Silicon) only — blocked on Linux by CORE-04",
        status=IN_PROGRESS,
        objective=(
            "Check that running the analyzers concurrently is faster than "
            "running them in sequence and yields exactly the same diagnostics "
            "— parallelism must not drop or duplicate findings."
        ),
        prerequisites=PRE_PY + " cppcheck installed and on PATH.",
        steps=[
            "cd coretrace",
            "python3 -B tests/BTP-STACK-ANALYZER-F7",
        ],
        expected=(
            "On Apple Silicon macOS: the script prints a `sync median`, an "
            "`async median` and a `speedup` above 1.0 (~1.9x observed). The "
            "`diagnostics` object is identical for the `sync` and `async` "
            "keys, and so is the `diagnostic fingerprints` list — same file, "
            "line, column, severity and message for every finding. Exit code "
            "0. On Linux the script stops with "
            "`FAIL: sync run did not return diagnostic fingerprints for: "
            "cppcheck` and exit code 1, because the harness compares two "
            "tools and one of them cannot start (see CORE-04). Testers on "
            "Linux: mark KO, quote that line, do not open a new anomaly."
        ),
    ),
    dict(
        id="CORE-09",
        component="coretrace",
        name="Configuration file and CLI precedence",
        category=SECONDARY,
        platform=BOTH,
        status=DONE,
        objective=(
            "Check that settings can be supplied by file and that a CLI flag "
            "overrides the file, as documented in docs/configuration.md."
        ),
        prerequisites=PRE_PY,
        steps=[
            "cd coretrace",
            "python3 -c \"import json;c=json.load(open('config/tool-config.json'));"
            "c['analysis']['invoke']=['ctrace_stack_analyzer'];"
            "c['output']['report_file']='/tmp/atp-from-config.json';"
            "json.dump(c,open('config/atp-prec.json','w'),indent=2)\"",
            "./build/ctrace --config config/atp-prec.json --input tests/null_pointer.c",
            "ls -l /tmp/atp-from-config.json",
            "./build/ctrace --config config/atp-prec.json --input tests/null_pointer.c "
            "--report-file /tmp/atp-from-cli.json",
            "ls -l /tmp/atp-from-cli.json",
            "rm -f config/atp-prec.json",
        ],
        expected=(
            "The first run writes /tmp/atp-from-config.json (path taken from "
            "the config file). The second writes /tmp/atp-from-cli.json, "
            "showing `--report-file` overrides the config. Both files parse "
            "as JSON and contain a `diagnosticsSummary` object. Exit code 0 "
            "for both."
        ),
    ),
    dict(
        id="CORE-10",
        component="coretrace",
        name="Configuration unit tests",
        category=SECONDARY,
        platform=BOTH,
        status=DONE,
        objective=(
            "Run the orchestrator's own test suite covering config parsing "
            "and precedence."
        ),
        prerequisites=PRE_BUILT,
        steps=[
            "cd coretrace",
            "ctest --test-dir build --output-on-failure",
        ],
        expected=(
            "`100% tests passed, 0 tests failed out of 1` "
            "(`ctrace_config_tests`). Exit code 0."
        ),
    ),
]
