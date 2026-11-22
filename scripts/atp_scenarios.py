# SPDX-License-Identifier: Apache-2.0
"""Scenario data for the CoreTrace Acceptance Test Plan.

Kept apart from the spreadsheet writer so that iterating on the plan between
test cycles is a data edit, not a formatting edit.

Every `steps` entry is a command a tester can paste verbatim from the ATP root
(/atp in the Linux image). Every `expected` entry is checkable without interpreting the tool's
intent: an exact counter, an exit code, a literal substring.

`eip` is the EIP feature number, set where a proof script (proofs/BTP-*-F<n>.py,
copied into the image) or the feature list establishes which feature a scenario
exercises. It is shown at the end of the Feature Name.
"""

CRITICAL = "Critical feature"
SECONDARY = "Secondary function"
INTERFACE = "User interface"

DONE = "Done"
IN_PROGRESS = "In progress"

LINUX = "Linux (Docker)"

# Where the test harness is published. The workbook is the only file delivered on the
# Innovation platform: everything else a tester needs is fetched from this repository.
ATP_REPO = "https://github.com/CoreTrace/ATP"

# Prerequisite fragments reused across scenarios, so a change to the setup
# contract does not have to be applied thirty times.
PRE_BUILT = "ENV-02 passed. All commands run from /atp inside the container opened by ./atp.sh linux."

PRE_PY = PRE_BUILT + " python3 >= 3.10 available."

SCENARIOS = [
    # ------------------------------------------------------------------ ENV
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
            'A macOS or Linux host (on Windows: WSL 2) with Docker Desktop or Docker '
            'Engine running, at least 4 CPUs and 8 GB of memory given to Docker, 10 GB of'
            ' free disk, git, and network access to GitHub and apt.llvm.org. Steps 1 to 4'
            ' run on the host (README.md, section 2). Without git, download the repository'
            ' from its GitHub page (Code, then Download ZIP), unzip it, open a terminal in'
            ' the folder you get (ATP-main) and start at step 3.'
            ' The build took 6 min 30 s on an 8-core laptop; allow up to 30 min on a '
            'slower machine or network.'
        ),
        steps=[
            f"git clone {ATP_REPO}.git",
            "cd ATP",
            "./atp.sh build-linux",
            "./atp.sh linux",
            "# inside the container:",
            "ls /atp",
            "id -u",
            "cat /atp/VERSIONS",
            "/atp/coretrace/build/ctrace --version",
        ],
        expected=(
            'Step 1 creates a folder named ATP that holds README.md and atp.sh. '
            '`./atp.sh build-linux` ends with `==> done — open a shell with: ./atp.sh '
            'linux`. Inside the container `ls /atp` lists the four repositories, '
            '`datasets` and `VERSIONS`; `id -u` prints `1000` (the unprivileged `ubuntu` '
            'account, not root); `cat /atp/VERSIONS` prints the four revisions listed in '
            'the Info & Access tab; `ctrace --version` prints `ctrace '
            'v0.85.0-109-g7de854e`.'
        ),
    ),

    # ---------------------------------------------------------------- STACK
    dict(
        id="STACK-01",
        eip="F1",
        component="coretrace-stack-analyzer",
        name="Static stack size and call-chain propagation",
        category=CRITICAL,
        platform=LINUX,
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
        eip="F1",
        component="coretrace-stack-analyzer",
        name="Dynamic stack usage (VLA / alloca) and unknown propagation",
        category=CRITICAL,
        platform=LINUX,
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
        eip="F1",
        component="coretrace-stack-analyzer",
        name="Infinite recursion detection",
        category=CRITICAL,
        platform=LINUX,
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
        eip="F1",
        component="coretrace-stack-analyzer",
        name="Stack pointer escape detection",
        category=CRITICAL,
        platform=LINUX,
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
        eip="F10",
        component="coretrace-stack-analyzer",
        name="Static stack-buffer overflow detection (F10)",
        category=CRITICAL,
        platform=LINUX,
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
            'The analyzer reports, in `vuln_off_by_one`, `stack buffer overflow on '
            "variable 'buf' (size 10)` with the note `index reaches 10 on every run of "
            'the function that returns (array last valid index: 9)`, and `Diagnostics '
            'summary: info=0, warning=4, error=0`. The F10 proof script prints `[F10] '
            'BTP-STACK-ANALYZER-F10: PASS` as its first line (`PASS` in green), then its '
            'evidence, and exits 0.'
        ),
    ),
    dict(
        id="STACK-06",
        eip="F2",
        component="coretrace-stack-analyzer",
        name="Memory intrinsic overflow and aliasing (F2)",
        category=CRITICAL,
        platform=LINUX,
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
            'The first command reports `potential stack buffer overflow in memcpy on '
            "variable 'buf'` with `destination stack buffer size: 10 bytes` and "
            '`requested 20 bytes to be copied/initialized`. The F2 proof covers memcpy, '
            'memset, deep aliasing and const-correctness: it prints `[F2] '
            'BTP-STACK-ANALYZER-F2: PASS` as its first line, then one `PASS` per check, '
            'and exits 0.'
        ),
    ),
    dict(
        id="STACK-07",
        eip="F1",
        component="coretrace-stack-analyzer",
        name="Configurable stack limit",
        category=SECONDARY,
        platform=LINUX,
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
        eip="F5",
        component="coretrace-stack-analyzer",
        name="Human, JSON and SARIF reporting (F5)",
        category=INTERFACE,
        platform=LINUX,
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
            '`JSON_OK` is printed. The SARIF line prints `coretrace-stack-analyzer 5`: '
            'the four warnings shown by step 2, plus one info-level diagnostic that '
            '`--warnings-only` hides there. The F5 proof runs the three formats over '
            'three fixtures and confirms diagnostic counts match across formats: it '
            'prints `[F5] BTP-STACK-ANALYZER-F5: PASS` as its first line, then about a '
            'thousand lines of raw output as evidence — scroll back up to read that first'
            ' line. Exit 0.'
        ),
    ),
    dict(
        id="STACK-09",
        eip="F8",
        component="coretrace-stack-analyzer",
        name="Itanium ABI mangling and demangling (F8)",
        category=SECONDARY,
        platform=LINUX,
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
            'Default human output shows both forms on one line, e.g. '
            '`_ZN12demo_symbols17scalar_parametersEidc '
            'demo_symbols::scalar_parameters(int, double, char)`. With `--demangle` only '
            'the readable signature remains. JSON prints the raw symbol '
            '`_ZN12demo_symbols17scalar_parametersEidc`. The F8 proof prints `[F8] '
            'BTP-STACK-ANALYZER-F8: PASS` as its first line, then the mangled and '
            'demangled symbols it checked, and exits 0.'
        ),
    ),
    dict(
        id="STACK-10",
        component="coretrace-stack-analyzer",
        name="Clean source produces no diagnostic",
        category=CRITICAL,
        platform=LINUX,
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
        platform=LINUX,
        status=DONE,
        objective=(
            "Check that the patterns that used to produce false positives "
            "(wrapper allocators, merged returns, vendor headers, Vulkan-style "
            "out-parameters) are still silent."
        ),
        prerequisites=(
            'ENV-02 passed. Run from /atp inside the container (its shell is bash). The '
            'list of fixtures is /atp/datasets/stack-no-false-positive.txt, so '
            '../datasets/ resolves from the analyzer repository.'
        ),
        steps=[
            "cd coretrace-stack-analyzer",
            "grep -v '^#' ../datasets/stack-no-false-positive.txt | grep -v '^$' | "
            "while read f; do out=$(./build/stack_usage_analyzer \"$f\" --warnings-only 2>&1); "
            "rc=$?; n=$(printf '%s\\n' \"$out\" | grep -c '!!'); echo \"$n exit=$rc $f\"; done",
        ],
        expected=(
            '15 lines, every one starting with `0 exit=0`. A line starting with a '
            'non-zero count is a false-positive regression; a line showing a non-zero '
            'exit is a file the analyzer could not analyse. Either way report the file '
            'name in Feedback. (The rest of test/false-positive-repro/ is not checked '
            'here: those fixtures reproduce one false positive while still containing a '
            'real defect, so they legitimately emit diagnostics. STACK-12 checks them '
            'against the expectations embedded in each file.)'
        ),
    ),
    dict(
        id="STACK-12",
        component="coretrace-stack-analyzer",
        name="Full regression suite, including the SMT pass",
        category=CRITICAL,
        platform=LINUX,
        status=DONE,
        objective=(
            "Run the whole fixture suite twice — once with the default "
            "engine, once with SMT refinement on the z3 backend — and check "
            "that both agree with the expectations embedded in the fixtures."
        ),
        prerequisites=PRE_PY + " Takes about one minute on 8 cores.",
        steps=[
            "cd coretrace-stack-analyzer",
            "python3 -u run_test.py --jobs 8",
        ],
        expected=(
            'The run ends with `All tests passed.` and `Passed N/N tests.` with no '
            'failure — 2916/2916 at the revision under test. Exit code 0. The report '
            'includes `(smt-z3)` lines, proving the SMT pass ran and did not change the '
            'verdicts.'
        ),
    ),
    dict(
        id="STACK-13",
        component="coretrace-stack-analyzer",
        name="CI adapter: artifacts and policy gate",
        category=SECONDARY,
        platform=LINUX,
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
        platform=LINUX,
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

    dict(
        id="STACK-15",
        eip="F1",
        component="coretrace-stack-analyzer",
        name="ABI analysis mode",
        category=SECONDARY,
        platform=LINUX,
        status=DONE,
        objective=(
            "Check that the second analysis mode is selectable and accounts "
            "for the frame differently from the default IR mode."
        ),
        prerequisites=PRE_PY,
        steps=[
            "cd coretrace-stack-analyzer",
            "./build/stack_usage_analyzer test/local-storage/c/stack-callee-caller.c "
            "--format=json | python3 -c \"import sys,json;d=json.load(sys.stdin);"
            "print(d['meta']['mode'],[(f['name'],f['localStack']) for f in d['functions']])\"",
            "./build/stack_usage_analyzer test/local-storage/c/stack-callee-caller.c "
            "--mode=abi --format=json | python3 -c \"import sys,json;d=json.load(sys.stdin);"
            "print(d['meta']['mode'],[(f['name'],f['localStack']) for f in d['functions']])\"",
        ],
        expected=(
            "The first line starts with `IR` and reports `bar` and `mano` with "
            "`localStack` 0. The second starts with `ABI` and reports the same "
            "two functions with `localStack` 32 — the ABI mode adds the "
            "caller-saved area the IR view does not model. `foo` is identical "
            "in both. A run where both modes print the same numbers means "
            "`--mode` was ignored."
        ),
    ),
    dict(
        id="STACK-16",
        component="coretrace-stack-analyzer",
        name="Whole-project analysis from compile_commands.json",
        category=CRITICAL,
        platform=LINUX,
        status=DONE,
        objective=(
            "Check the way the analyzer is meant to be used on a real "
            "codebase: read a compile database, analyse every translation "
            "unit it lists, and aggregate one summary — here the analyzer "
            "analysing its own source."
        ),
        prerequisites=PRE_BUILT + " Takes about 1 minute on 8 cores.",
        steps=[
            "cd coretrace-stack-analyzer",
            "./build/stack_usage_analyzer --compile-commands=build/compile_commands.json "
            "--analysis-profile=fast --exclude-dir=build/_deps --warnings-only",
        ],
        expected=(
            'The run ends with a single aggregate line of the form `Total diagnostics '
            'summary: info=0, warning=<n>, error=0 (across <m> files)` — observed '
            '`warning=6` across 53 files. Those two numbers depend on the platform and '
            'are not the check. What must hold: several dozen files analysed in one '
            'invocation, `error=0` (the project keeps its own CI gate green), and no line'
            ' starting with `Failed to analyze`.'
        ),
    ),

    dict(
        id='STACK-17',
        component='coretrace-stack-analyzer',
        name='Security diagnostics across the fifteen categories of the corpus',
        category=CRITICAL,
        platform=LINUX,
        status=DONE,
        objective=(
            'Check that the analyzer reports the defect each category of the security '
            'corpus is built around, beyond stack overflows: injection, format strings, '
            'integer overflows, null dereferences, out-of-bounds reads, resource '
            'lifetime, TOCTOU and others.'
        ),
        prerequisites=PRE_PY + " Shell is bash.",
        steps=[
            'cd coretrace-stack-analyzer',
            'for f in test/security/*/*.c; do printf \'%s: \' "${f#test/security/}"; ./build/stack_usage_analyzer "$f" --resource-model=models/resource-lifetime/generic.txt --format=json 2>/dev/null | python3 -c "import sys,json;print(\' \'.join(sorted({d[\'ruleId\'] for d in json.load(sys.stdin)[\'diagnostics\'] if d[\'severity\']!=\'INFO\'})))"; done',
        ],
        expected=(
            '24 lines, one per file, each giving the rules reported as warnings or '
            'errors. Every category shows its own rule: buffer-overflow '
            '`StackBufferOverflow.EveryRun`; command-injection '
            '`CommandInjection.NonLiteralCommand`; format-string '
            '`FormatString.NonLiteral`; integer-overflow '
            '`IntegerOverflow.SignedArithmetic`; memory-leak '
            '`ResourceLifetime.MissingRelease`; null-dereference '
            '`NullPointerDereference`; oob-read `OutOfBoundsRead.HeapIndex` or '
            '`OutOfBoundsRead.MissingNullTerminator`; sizeof-pitfall `SizeofPitfall`; '
            'stack-escape `StackPointerEscape`; toctou `TOCTOU.PathCheckThenUse`; '
            'type-confusion `TypeConfusion.IncompatibleStructView`; uninitialized '
            '`UninitializedLocalRead`; unsafe-functions `UnsafeFunction.DeprecatedGets`; '
            'use-after-free `ResourceLifetime.UseAfterRelease`; variadic-mismatch '
            '`VariadicFormatMismatch`. Two oob-read files, heap-index-masked.c and '
            'heap-index-modulo.c, are safe variants and print nothing after their name. A'
            ' Python `Traceback` on a line means the analyzer could not analyse that '
            'file. The `--resource-model` option is what makes the memory-leak and '
            'use-after-free categories report.'
        ),
    ),

    # ----------------------------------------------------------------- CONC
    dict(
        id="CONC-01",
        component="coretrace-concurrency-analyzer",
        name="Data race on an unsynchronised global",
        category=CRITICAL,
        platform=LINUX,
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
        eip="F12",
    ),
    dict(
        id="CONC-02",
        component="coretrace-concurrency-analyzer",
        name="Thread handle never joined or detached",
        category=CRITICAL,
        platform=LINUX,
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
        eip="F12",
    ),
    dict(
        id="CONC-03",
        component="coretrace-concurrency-analyzer",
        name="Deadlock through lock-order inversion",
        category=CRITICAL,
        platform=LINUX,
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
        eip="F12",
    ),
    dict(
        id="CONC-04",
        component="coretrace-concurrency-analyzer",
        name="Deadlock through a three-lock cycle",
        category=SECONDARY,
        platform=LINUX,
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
        eip="F12",
    ),
    dict(
        id="CONC-05",
        component="coretrace-concurrency-analyzer",
        name="No false positive on correctly synchronised code",
        category=CRITICAL,
        platform=LINUX,
        status=DONE,
        objective=(
            "Check that code protected by lock_guard, atomics, a condition "
            "variable or C++20 jthread auto-join produces no diagnostic."
        ),
        prerequisites=(
            'ENV-02 passed. Run from /atp inside the container (its shell is bash). The '
            'list of fixtures is /atp/datasets/conc-no-false-positive.txt.'
        ),
        steps=[
            'cd coretrace-concurrency-analyzer',
            'n=0; bad=0; while read f; do n=$((n+1)); s=$(./build/coretrace_concurrency_analyzer "$f" --analyze 2>&1 | tail -1); case "$s" in *"info=0, warning=0, error=0"*) ;; *) bad=$((bad+1)); echo "BAD $s | $f";; esac; done < <(grep -v \'^#\' ../datasets/conc-no-false-positive.txt | grep -v \'^$\'); echo "checked=$n bad=$bad"',
            './build/coretrace_concurrency_analyzer tests/fixtures/concurrency-cxx20/cpp_jthread_auto_join_no_missing_join.cpp --analyze -- -std=c++20 | tail -1',
        ],
        expected=(
            'The loop prints `checked=28 bad=0` and no `BAD` line. Each `BAD` line is a '
            'false positive, or a file that could not be analysed: report the file name '
            'in Feedback. The C++20 jthread case prints `Diagnostics summary: info=0, '
            'warning=0, error=0` — a jthread joins in its destructor, so it must not be '
            'reported as a missing join. (The `-- -std=c++20` suffix is required: without'
            ' it clang defaults to an older standard and the fixture fails to compile.)'
        ),
        eip="F12",
    ),
    dict(
        id="CONC-06",
        component="coretrace-concurrency-analyzer",
        name="Rule selection",
        category=SECONDARY,
        platform=LINUX,
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
        eip="F12",
    ),
    dict(
        id="CONC-07",
        component="coretrace-concurrency-analyzer",
        name="Human, JSON and SARIF reporting",
        category=INTERFACE,
        platform=LINUX,
        status=DONE,
        objective=(
            "Check that concurrency diagnostics are available in the three "
            "output formats with the same content."
        ),
        prerequisites=PRE_PY,
        steps=[
            'cd coretrace-concurrency-analyzer',
            'F=tests/fixtures/concurrency/data-race/data_race_basic.c',
            './build/coretrace_concurrency_analyzer $F --analyze --format=json | python3 -m json.tool > /dev/null && echo JSON_OK',
            './build/coretrace_concurrency_analyzer $F --analyze --format=json | python3 -c "import sys,json;d=json.load(sys.stdin)[\'diagnostics\'][0];print(d[\'ruleId\'],d[\'cwe\'],d[\'confidence\'],sorted(d[\'details\']))"',
            './build/coretrace_concurrency_analyzer $F --analyze --format=sarif > /tmp/conc07.sarif',
            'python3 -c "import json;d=json.load(open(\'/tmp/conc07.sarif\'));r=d[\'runs\'][0];print(r[\'tool\'][\'driver\'][\'name\'],len(r[\'results\']),r[\'results\'][0][\'ruleId\'])"',
        ],
        expected=(
            "`JSON_OK` is printed. Step 4 prints `DataRaceGlobal CWE-362 HIGH ['message',"
            " 'notes', 'properties']`: the JSON diagnostic carries its rule, CWE, "
            'confidence, notes and properties. The last command prints '
            '`coretrace-concurrency-analyzer 1 DataRaceGlobal`: the SARIF report holds '
            'the same single diagnostic.'
        ),
        eip="F12",
    ),
    dict(
        id="CONC-08",
        component="coretrace-concurrency-analyzer",
        name="Unit, architecture and golden-output test suites",
        category=CRITICAL,
        platform=LINUX,
        status=DONE,
        objective=(
            "Run the repository's own suites: CTest for the C++ unit and "
            "architecture tests, pytest for the fixture-embedded expected "
            "human output."
        ),
        prerequisites=(
            'ENV-02 passed. Run from /atp inside the container. Python and pytest are '
            'preinstalled. Takes about 3 minutes.'
        ),
        steps=['cd coretrace-concurrency-analyzer',
         'ctest --test-dir build --output-on-failure',
         'CORETRACE_ANALYZER_BIN=./build/coretrace_concurrency_analyzer python3 -m pytest '
         'tests/integration/cli/test_human_output_golden.py -q'],
        expected=(
            'CTest prints `100% tests passed, 0 tests failed out of 20`. pytest prints '
            '`10 passed`; each fixture matches its embedded EXPECT-HUMAN-DIAGNOSTICS '
            'block. Do NOT run the whole tests/integration/cli directory: '
            'test_analyzer.py requires the separate coretrace-testkit package.'
        ),
        eip="F12",
    ),
    dict(
        id="CONC-09",
        component="coretrace-concurrency-analyzer",
        name="Error handling on invalid input",
        category=SECONDARY,
        platform=LINUX,
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
        eip="F12",
    ),

    dict(
        id="CONC-10",
        component="coretrace-concurrency-analyzer",
        name="Public C++ API through an external consumer",
        category=SECONDARY,
        platform=LINUX,
        status=DONE,
        objective=(
            "Check that the analyzer is consumable as a library by another "
            "CMake project, which is how CoreTrace is meant to be embedded."
        ),
        prerequisites=(
            'ENV-02 passed. Run from /atp inside the container. LLVM 20 and CMake are '
            'provided by the image. The consumer reuses the coretrace-compiler and '
            "coretrace-log sources already present in the analyzer's build tree "
            '(build/_deps), so no network access is needed. The build takes about 30 '
            'seconds on 8 cores.'
        ),
        steps=[
            'cd coretrace-concurrency-analyzer',
            'P=$(llvm-config --prefix); D=$PWD/build/_deps; cmake -S extern-project -B extern-project/build -G Ninja -DFETCHCONTENT_SOURCE_DIR_CC=$D/cc-src -DFETCHCONTENT_SOURCE_DIR_CORETRACE_LOGGER=$D/coretrace_logger-src -DLLVM_DIR=$P/lib/cmake/llvm -DClang_DIR=$P/lib/cmake/clang -DCLANG_EXECUTABLE=$P/bin/clang -DCLANG_RESOURCE_DIR=$($P/bin/clang -print-resource-dir)',
            'cmake --build extern-project/build -j8',
            './extern-project/build/concurrency_consumer tests/fixtures/concurrency/data-race/data_race_basic.c',
        ],
        expected=(
            'Step 2 prints `-- Using local concurrency analyzer source` and ends with `--'
            ' Build files have been written to: '
            '/atp/coretrace-concurrency-analyzer/extern-project/build`. Step 3 compiles '
            'and links without error. Step 4 prints `Consumer compilation succeeded in bc'
            ' mode, payload=<n> bytes` (4524 observed): a separate CMake project linked '
            'the analyzer library and compiled a source through its public API.'
        ),
        eip="F12",
    ),

    dict(
        id='CONC-11',
        eip='F12',
        component='coretrace-concurrency-analyzer',
        name='The eight other concurrency rules',
        category=CRITICAL,
        platform=LINUX,
        status=DONE,
        objective=(
            'Check each concurrency rule that CONC-01 to CONC-04 do not cover: every '
            'rule, selected alone, reports its defect on a fixture written for it.'
        ),
        prerequisites=PRE_BUILT,
        steps=[
            'cd coretrace-concurrency-analyzer',
            './build/coretrace_concurrency_analyzer tests/fixtures/concurrency/condition-variable/condition_variable_spurious.c --analyze --rules=condition-wait | grep -E "ruleId|summary"',
            './build/coretrace_concurrency_analyzer tests/fixtures/concurrency/process/fork_after_thread_creation.c --analyze --rules=fork-after-thread | grep -E "ruleId|summary"',
            './build/coretrace_concurrency_analyzer tests/fixtures/concurrency/process/fork_without_wait.c --analyze --rules=unreaped-child | grep -E "ruleId|summary"',
            './build/coretrace_concurrency_analyzer tests/fixtures/concurrency/missing-join/missing_join_multiple.c --analyze --rules=thread-arg-escape | grep -E "ruleId|summary"',
            './build/coretrace_concurrency_analyzer tests/fixtures/concurrency/signal-handler/signal_mutex_deadlock.c --analyze --rules=unsafe-signal-handler | grep -E "ruleId|summary"',
            './build/coretrace_concurrency_analyzer tests/fixtures/concurrency/atomic-ordering/publish_relaxed_load.c --analyze --rules=weak-publication | grep -E "ruleId|summary"',
            './build/coretrace_concurrency_analyzer tests/fixtures/concurrency/use-after-free/use_after_free_callback.c --analyze --rules=thread-arg-freed | grep -E "ruleId|summary"',
            './build/coretrace_concurrency_analyzer tests/fixtures/concurrency/thread-local/c_tls_dangling_ptr.c --analyze --rules=thread-local-escape | grep -E "ruleId|summary"',
        ],
        expected=(
            'Each command prints one `ruleId:` line and one summary line. In order: '
            '`ruleId: ConditionWaitWithoutPredicate`, `ruleId: ForkAfterThreadCreation`, '
            '`ruleId: UnreapedChildProcess`, `ruleId: ThreadArgumentEscapesFrame`, '
            '`ruleId: UnsafeSignalHandler`, `ruleId: WeakPublicationOrdering`, `ruleId: '
            'ThreadArgumentFreedEarly`, `ruleId: ThreadLocalOutlivesThread`. The summary '
            'is `Diagnostics summary: info=0, warning=0, error=1` for six of them, and '
            '`Diagnostics summary: info=0, warning=1, error=0` for the third '
            '(unreaped-child) and the sixth (weak-publication), which are warnings.'
        ),
    ),

    # ------------------------------------------------------------------ RUN
    dict(
        id="RUN-01",
        eip="F4",
        component="coretrace-runtime-analyzer",
        name="Instrumented build, execution and event collection (F4)",
        category=CRITICAL,
        platform=LINUX,
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
            "The script reports `instrumented_binary_generated=OK`, "
            "`instrumented_binary_executable=OK`, `coretrace_lines_collected=OK`, "
            "`entry_events_collected=OK`, `exit_events_collected=OK`, then "
            "`[F4] result=OK`, exit 0. The collection block shows "
            "`entry_events=2` and `exit_events=2`."
        ),
    ),
    dict(
        id="RUN-02",
        eip="F11",
        component="coretrace-runtime-analyzer",
        name="Heap buffer overflow detected at runtime (F11)",
        category=CRITICAL,
        platform=LINUX,
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
            'Output contains `ct: heap-buffer-overflow WRITE of size 1` with an '
            '`access=...:18:15` line, an `alloc_site=...:6:63` line and `alloc_size=8`. '
            'Status lines `runtime_analyzer_exit_reports_finding=OK` (the analyzer exits '
            '1 when it reports a finding), `heap_buffer_overflow_reported=OK`, '
            '`write_overflow_reported=OK`, `bounds_errors_collected=OK`, '
            '`program_continued_after_detection=OK`, then a final `PASS`. The script '
            'itself exits 0.'
        ),
    ),
    dict(
        id="RUN-05",
        eip="F4",
        component="coretrace-runtime-analyzer",
        name="Batch mode over a test directory",
        category=SECONDARY,
        platform=LINUX,
        status=DONE,
        objective=(
            "Check that every source under a directory is compiled and run as "
            "its own instrumented binary, and that per-file results are "
            "aggregated instead of the run stopping at the first failure."
        ),
        prerequisites=PRE_BUILT,
        steps=[
            'cd coretrace-runtime-analyzer',
            'mkdir -p /tmp/atp-rt-src && cp test/ct_alloc_basic.c test/ct_autofree_local.c test/ct_new_delete.cpp /tmp/atp-rt-src/',
            './build/runtime-analyzer --test-dir /tmp/atp-rt-src --output-dir /tmp/atp-rt-out; echo "exit=$?"',
        ],
        expected=(
            'The batch block reports `tests=3`, `compile_failures=0` and '
            '`runtime_failures=0`. Each source has a `[PASS]` line naming the generated '
            'binary and `exit_code=0`. Under each file the analyzer lists the `memory '
            'leak` warnings it found in that program. The command ends with `exit=1`: the'
            ' analyzer itself exits 1 because it reports those leaks, even though each '
            'test program exits 0. That exit code is expected here, it is not a failure '
            'of the batch.'
        ),
    ),


    dict(
        id="RUN-07",
        eip="F3",
        component="coretrace-runtime-analyzer",
        name="Instrumentation modules: trace, alloc, bounds",
        category=CRITICAL,
        platform=LINUX,
        status=DONE,
        objective=(
            "Check that each instrumentation module of the CoreTrace compiler can "
            "be switched on by itself, and that each one produces its own kind of "
            "runtime event."
        ),
        prerequisites=PRE_BUILT,
        steps=[
            "cd coretrace-runtime-analyzer",
            "./build/runtime-analyzer -o /tmp/f3-trace -- --ct-modules=trace "
            "test/examples/fixtures/hello.c; echo \"exit=$?\"",
            "./build/runtime-analyzer -o /tmp/f3-alloc -- --ct-modules=alloc "
            "test/ct_alloc_basic.c; echo \"exit=$?\"",
            "./build/runtime-analyzer -o /tmp/f3-bounds -- --ct-modules=alloc,bounds "
            "test/findings/heap_overflow_write.c; echo \"exit=$?\"",
        ],
        expected=(
            "First run (trace): `entry_events=1`, `exit_events=1`, `allocation_events=0`, "
            "then `exit=0`. Second run (alloc): `entry_events=0`, `allocation_events=8`, a "
            "`memory leak of 24 bytes` warning, then `exit=1` — the analyzer exits 1 when "
            "it reports a finding. Third run (alloc and bounds): `bounds_errors=1` and "
            "`test/findings/heap_overflow_write.c:8:15: error: heap-buffer-overflow WRITE "
            "of size 4 [heap-buffer-overflow, CWE-122]`, then `exit=1`; its `exit_code=134` "
            "line is the instrumented program being stopped at the overflow. Each module "
            "leaves the counters of the others at zero."
        ),
    ),

    dict(
        id='RUN-08',
        eip='F11',
        component='coretrace-runtime-analyzer',
        name='Memory defects found at runtime',
        category=CRITICAL,
        platform=LINUX,
        status=DONE,
        objective=(
            'Check that the runtime analyzer finds each kind of memory defect it knows, '
            'names it with its CWE, and stays silent on a correct program.'
        ),
        prerequisites=PRE_BUILT + " Shell is bash.",
        steps=[
            'cd coretrace-runtime-analyzer',
            'for f in test/findings/*.c; do out=$(./build/runtime-analyzer -o /tmp/atp-finding -- --ct-modules=alloc,bounds "$f" 2>&1); rc=$?; echo "$(basename "$f") exit=$rc $(printf \'%s\\n\' "$out" | grep -E \'error:|warning:\' | head -1)"; done',
        ],
        expected=(
            'Seven lines. `double_free.c exit=1` with `[double-free, CWE-415]`; '
            '`heap_overflow_read.c exit=1` with `READ of size 4 [heap-buffer-overflow, '
            'CWE-125]`; `heap_overflow_write.c exit=1` with `WRITE of size 4 '
            '[heap-buffer-overflow, CWE-122]`; `memory_leak.c exit=1` with `[memory-leak,'
            ' CWE-401]`; `no_findings.c exit=0` with nothing after it; '
            '`stack_overflow_write.c exit=1` with `[stack-buffer-overflow, CWE-121]`; '
            '`use_after_free.c exit=1` with `[heap-use-after-free, CWE-416]`. The '
            'analyzer exits 1 when it reports a finding and 0 when it finds none.'
        ),
    ),

    dict(
        id='RUN-09',
        component='coretrace-runtime-analyzer',
        name='Unit, API and command-line test suite',
        category=CRITICAL,
        platform=LINUX,
        status=DONE,
        objective=(
            "Run the runtime analyzer's own test suite: unit tests, the library API, the "
            'command line, the fixtures and the installed layout.'
        ),
        prerequisites=PRE_BUILT + " Takes about 30 seconds.",
        steps=[
            'cd coretrace-runtime-analyzer',
            'ctest --test-dir build --output-on-failure',
        ],
        expected=(
            '`100% tests passed, 0 tests failed out of 17`. Exit code 0.'
        ),
    ),

    # ----------------------------------------------------------------- CORE
    dict(
        id="CORE-01",
        component="coretrace",
        name="CLI help and version",
        category=INTERFACE,
        platform=LINUX,
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
            '`--help` lists at least `--static`, `--dyn`, `--invoke`, `--input`, '
            '`--sarif-format`, `--config`, `--fail-on`, `--ipc` and `--jobs`, and ends '
            'with an Examples section. `--version` prints `ctrace v0.85.0-109-g7de854e`, '
            'the revision under test.'
        ),
    ),
    dict(
        id="CORE-05",
        component="coretrace",
        name="SARIF report file",
        category=INTERFACE,
        platform=LINUX,
        status=DONE,
        objective=(
            "Check that CoreTrace can write a valid SARIF report to a chosen "
            "path, for consumption by GitHub code scanning."
        ),
        prerequisites=PRE_PY,
        steps=[
            'cd coretrace',
            './build/ctrace --invoke ctrace_stack_analyzer --input tests/null_pointer.c --sarif-format --report-file /tmp/atp-core.sarif; echo "exit=$?"',
            'python3 -c "import json;d=json.load(open(\'/tmp/atp-core.sarif\'));print(sorted(d),d[\'runs\'][0][\'tool\'][\'driver\'][\'name\'],len(d[\'runs\'][0][\'results\']))"',
        ],
        expected=(
            'Step 2 ends with `Verdict: info=0, warning=1, error=1, fail-on=error (exit '
            'code 2)` and `exit=2`: the analysed file holds an error-level defect, and 2 '
            'is the exit code ctrace gives a CI job in that case, not a failure of the '
            "scenario. Step 3 prints `['$schema', 'runs', 'version'] "
            'ctrace_stack_analyzer 2`: the report is a SARIF document with its three '
            'top-level keys, and it carries the two findings.'
        ),
        eip="F5",
    ),
    dict(
        id="CORE-06",
        component="coretrace",
        name="HTTP server mode",
        category=CRITICAL,
        platform=LINUX,
        status=DONE,
        objective=(
            "Check that CoreTrace can serve analyses over HTTP so a UI or a "
            "CI runner can drive it without spawning a process per request."
        ),
        prerequisites=PRE_BUILT + " curl is available in the image. TCP port 8099 free.",
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
        eip="F9",
    ),
    dict(
        id="CORE-07",
        component="coretrace",
        name="Server shutdown is token-protected",
        category=CRITICAL,
        platform=LINUX,
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
        eip="F9",
    ),
    dict(
        id="CORE-09",
        component="coretrace",
        name="Configuration file and CLI precedence",
        category=SECONDARY,
        platform=LINUX,
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
            'The first run writes /tmp/atp-from-config.json (path taken from the config '
            'file). The second writes /tmp/atp-from-cli.json, showing `--report-file` '
            'overrides the config. Both `ls -l` lines show an existing file, and both '
            'runs print a JSON report containing a `diagnosticsSummary` object. Each run '
            'ends with `Verdict: info=0, warning=1, error=1, fail-on=error (exit code '
            '2)`: the analysed file holds an error-level defect, which is expected here.'
        ),
    ),
    dict(
        id="CORE-10",
        component="coretrace",
        name="Orchestrator test suite",
        category=SECONDARY,
        platform=LINUX,
        status=DONE,
        objective=(
            "Run the orchestrator's own test suite: configuration parsing and precedence,"
            ' exit-code policy, SARIF and report files, the HTTP server, and the bridges '
            'to the stack and concurrency analyzers.'
        ),
        prerequisites=PRE_BUILT + " Takes less than a minute.",
        steps=[
            "cd coretrace",
            "ctest --test-dir build --output-on-failure",
        ],
        expected=(
            '`100% tests passed, 0 tests failed out of 99`. Exit code 0.'
        ),
    ),
    dict(
        id="CORE-11",
        eip="F7",
        component="coretrace",
        name="Parallel tool execution",
        category=SECONDARY,
        platform=LINUX,
        status=DONE,
        objective=(
            "Check that running the analysis tools in parallel gives exactly the "
            "same diagnostics as running them one after the other."
        ),
        prerequisites=PRE_PY + " cppcheck is installed in the image.",
        steps=[
            "cd coretrace",
            "python3 tests/BTP-STACK-ANALYZER-F7 --ctrace-bin ./build/ctrace --iterations 1 "
            "--warmups 0 --min-speedup-ratio 0; echo \"exit=$?\"",
        ],
        expected=(
            "The script prints `sync model: sequential CoreTrace tool invocations with -j1`, "
            "`async model: parallel CoreTrace tool invocations with -j4`, a `speedup:` line, "
            "and a `diagnostics:` line whose `\"async\"` and `\"sync\"` entries hold the "
            "same counts for `cppcheck` and `ctrace_stack_analyzer`. It ends with `exit=0`: "
            "the script exits non-zero when the two modes disagree. The speed-up value "
            "depends on the machine and is not the check."
        ),
    ),
    dict(
        id="CORE-12",
        eip="F6",
        component="coretrace",
        name="Code style check on the four repositories",
        category=SECONDARY,
        platform=LINUX,
        status=DONE,
        objective=(
            "Check that the code style pipeline is reproducible: the format check "
            "the CI runs passes, unchanged, on each repository."
        ),
        prerequisites=PRE_BUILT + " clang-format 20 is installed in the image.",
        steps=[
            "(cd coretrace && ./scripts/format-check.sh); echo \"exit=$?\"",
            "(cd coretrace-stack-analyzer && ./scripts/format-check.sh); echo \"exit=$?\"",
            "(cd coretrace-concurrency-analyzer && ./scripts/format-check.sh); echo \"exit=$?\"",
            "(cd coretrace-runtime-analyzer && ./scripts/format-check.sh); echo \"exit=$?\"",
        ],
        expected=(
            "Each of the four commands prints `Checking formatting on <n> ... files...` "
            "(107, 637, 106 and 24 files), then `Formatting is clean.` and `exit=0`."
        ),
    ),
    dict(
        id='CORE-13',
        component='coretrace',
        name='Several analyzers in one run, one merged verdict',
        category=CRITICAL,
        platform=LINUX,
        status=DONE,
        objective=(
            'Check what the orchestrator is for: one command runs two analyzers on the '
            'same file, and their findings are merged into a single verdict and exit '
            'code.'
        ),
        prerequisites=PRE_BUILT,
        steps=[
            'cd coretrace',
            './build/ctrace --invoke ctrace_stack_analyzer,coretrace-concurrency-analyzer --input ../coretrace-concurrency-analyzer/tests/fixtures/concurrency/data-race/data_race_basic.c --report-file /tmp/atp-multi.json; echo "exit=$?"',
        ],
        expected=(
            'The log shows both tools running: `Running coretrace-concurrency-analyzer on'
            ' 1 file(s)` and `Running CoreTrace Stack Analyzer on`. Each reports its own '
            'summary: `(coretrace-concurrency-analyzer) Diagnostics summary: info=0, '
            'warning=0, error=1` and `(ctrace_stack_analyzer) Diagnostics summary: '
            'info=1, warning=2, error=0`. The last line adds them up: `Verdict: info=1, '
            'warning=2, error=1, fail-on=error (exit code 2)`, then `exit=2` — the data '
            'race is an error-level finding.'
        ),
    ),
]

# The EIP features of the toolchain. F1 to F11 are those of the Beta Test Plan
# (June 2026); F12 was added since. Shown on the Info & Access tab next to the
# scenarios that carry each number.
FEATURES = {
    "F1": "Stack usage analysis (IR and ABI modes)",
    "F2": "Advanced stack diagnostics (memcpy/memset, aliasing, const-correctness)",
    "F3": "Instrumentation modules (trace, alloc, bounds)",
    "F4": "Runtime analyzer",
    "F5": "SARIF, JSON and human-readable output",
    "F6": "Code style checks (format, format-check)",
    "F7": "Parallel (asynchronous) tool execution",
    "F8": "Mangle/demangle, Itanium ABI",
    "F9": "IPC for the GUI and VS Code clients",
    "F10": "Static stack-buffer overflow analysis",
    "F11": "Overflow detection at runtime",
    "F12": "Static concurrency analysis",
}
