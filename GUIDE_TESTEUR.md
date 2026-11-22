# Parcours testeur — ATP CoreTrace (partie toolchain)

Ce guide accompagne la **partie 1** du plan (la toolchain). Le point d'entrée du
plan est `README.md` : lisez-le d'abord, il indique quel document ouvrir et quand.

Ce guide reprend, dans l'ordre, les commandes des 44 scénarios toolchain du
classeur ATP. Les commandes et les résultats attendus sont ceux de la colonne
*Steps* et *Expected results* du classeur, en anglais ; copiez les commandes
depuis ce fichier plutôt que depuis une cellule Excel.

La **partie 2** (l'application de bureau, scénarios `GUI-F…`) a son propre
environnement et sa propre notice : voir la section 5 de `README.md`.

## Avant de commencer

1. Lisez `README.md` (prérequis, que faire si le build échoue).
2. Démarrez Docker et ouvrez un terminal.
3. Déroulez `ENV-02` ci-dessous : il récupère le dépôt (si ce n'est pas déjà fait),
   construit l'image et ouvre le conteneur.

À partir de là, **toutes les commandes se tapent dans le conteneur**. Chaque
bloc commence par `cd /atp` pour repartir du bon dossier. Si vous quittez le
conteneur (`exit`), relancez simplement `./atp.sh linux`.

Pour chaque scénario, remplissez la colonne **Feedback** du classeur avec `OK`,
`KO` ou `Not run`, puis ce que vous avez vu. `OK` seulement si **tout** ce qui
est décrit dans « Attendu » est observé.

## ENV — environnement

### ENV-02 — Linux test image build (Docker)

```bash
git clone https://github.com/CoreTrace/ATP.git
cd ATP
./atp.sh build-linux
./atp.sh linux
# inside the container:
ls /atp
id -u
cat /atp/VERSIONS
/atp/coretrace/build/ctrace --version
```

**Attendu :** Step 1 creates a folder named ATP that holds README.md and atp.sh. `./atp.sh build-linux` ends with `==> done — open a shell with: ./atp.sh linux`. Inside the container `ls /atp` lists the four repositories, `datasets` and `VERSIONS`; `id -u` prints `1000` (the unprivileged `ubuntu` account, not root); `cat /atp/VERSIONS` prints the four revisions listed in the Info & Access tab; `ctrace --version` prints `ctrace v0.85.0-109-g7de854e`.

## STACK — analyseur de pile (coretrace-stack-analyzer)

### STACK-01 — Static stack size and call-chain propagation (F1)

```bash
cd /atp
cd coretrace-stack-analyzer
./build/stack_usage_analyzer test/local-storage/c/stack-callee-caller.c --format=json > /tmp/stack01.json
python3 -c "import json;d=json.load(open('/tmp/stack01.json'));[print(f['name'],f['localStack'],f['maxStack']) for f in d['functions']]"
```

**Attendu :** The JSON parses and prints one line per function. `foo` has a large `localStack` equal to its `maxStack` (it calls nothing). `bar` and `mano` have `localStack` 0 but the same `maxStack` as `foo` — the callee frame was propagated up the call chain, which is the point of the check. A `maxStack` equal to `localStack` on every function would be a failure.

### STACK-02 — Dynamic stack usage (VLA / alloca) and unknown propagation (F1)

```bash
cd /atp
cd coretrace-stack-analyzer
./build/stack_usage_analyzer test/vla/vla-scanf.c --format=json > /tmp/stack02.json
python3 -c "import json;d=json.load(open('/tmp/stack02.json'));[print(f['name'],f['hasDynamicAlloca'],f['maxStackUnknown']) for f in d['functions']]"
./build/stack_usage_analyzer test/vla/vla-scanf.c --warnings-only
```

**Attendu :** For function `main`: `hasDynamicAlloca` is true and `maxStackUnknown` is true. The human output contains `allocation performed via alloca/VLA` and `size is unbounded at compile time`.

### STACK-03 — Infinite recursion detection (F1)

```bash
cd /atp
cd coretrace-stack-analyzer
./build/stack_usage_analyzer test/recursion/c/infinite-recursion.c --warnings-only
./build/stack_usage_analyzer test/recursion/c/limited-recursion.c --warnings-only
```

**Attendu :** First run: `[!!!Error] unconditional self recursion detected (no base case)` and `Diagnostics summary: info=0, warning=0, error=1`. Second run: `Diagnostics summary: info=0, warning=0, error=0` — no diagnostic on the bounded case.

### STACK-04 — Stack pointer escape detection (F1)

```bash
cd /atp
cd coretrace-stack-analyzer
./build/stack_usage_analyzer test/security/stack-escape/11_return_local.c --warnings-only
```

**Attendu :** Output contains `stack pointer escape: address of variable 'x' escapes this function` and the note `escape via return statement (pointer to stack returned to caller)`.

### STACK-05 — Static stack-buffer overflow detection (F10)

```bash
cd /atp
cd coretrace-stack-analyzer
./build/stack_usage_analyzer test/security/buffer-overflow/01_buffer_overflow.c --warnings-only
python3 -B BTP-STACK-ANALYZER-F10.py
```

**Attendu :** The analyzer reports, in `vuln_off_by_one`, `stack buffer overflow on variable 'buf' (size 10)` with the note `index reaches 10 on every run of the function that returns (array last valid index: 9)`, and `Diagnostics summary: info=0, warning=4, error=0`. The F10 proof script prints `[F10] BTP-STACK-ANALYZER-F10: PASS` as its first line (`PASS` in green), then its evidence, and exits 0.

### STACK-06 — Memory intrinsic overflow and aliasing (F2)

```bash
cd /atp
cd coretrace-stack-analyzer
./build/stack_usage_analyzer test/cpy-buffer/bad-usage-memcpy.c --warnings-only
python3 -B BTP-STACK-ANALYZER-F2.py
```

**Attendu :** The first command reports `potential stack buffer overflow in memcpy on variable 'buf'` with `destination stack buffer size: 10 bytes` and `requested 20 bytes to be copied/initialized`. The F2 proof covers memcpy, memset, deep aliasing and const-correctness: it prints `[F2] BTP-STACK-ANALYZER-F2: PASS` as its first line, then one `PASS` per check, and exits 0.

### STACK-07 — Configurable stack limit (F1)

```bash
cd /atp
cd coretrace-stack-analyzer
./build/stack_usage_analyzer test/local-storage/c/stack-exhaustion-large-frame.c --warnings-only
./build/stack_usage_analyzer test/local-storage/c/stack-exhaustion-large-frame.c --stack-limit=64KiB --warnings-only
```

**Attendu :** Both runs report `[!!!Error] potential stack overflow: exceeds limit of ...`. The first names `8388608 bytes` (8 MiB default), the second `65536 bytes`, showing the option was applied.

### STACK-08 — Human, JSON and SARIF reporting (F5)

```bash
cd /atp
cd coretrace-stack-analyzer
./build/stack_usage_analyzer test/security/buffer-overflow/01_buffer_overflow.c --warnings-only
./build/stack_usage_analyzer test/security/buffer-overflow/01_buffer_overflow.c --format=json | python3 -m json.tool > /dev/null && echo JSON_OK
./build/stack_usage_analyzer test/security/buffer-overflow/01_buffer_overflow.c --format=sarif > /tmp/stack08.sarif
python3 -c "import json;d=json.load(open('/tmp/stack08.sarif'));print(d['runs'][0]['tool']['driver']['name'],len(d['runs'][0]['results']))"
python3 -B BTP-STACK-ANALYZER-F5.py
```

**Attendu :** `JSON_OK` is printed. The SARIF line prints `coretrace-stack-analyzer 5`: the four warnings shown by step 2, plus one info-level diagnostic that `--warnings-only` hides there. The F5 proof runs the three formats over three fixtures and confirms diagnostic counts match across formats: it prints `[F5] BTP-STACK-ANALYZER-F5: PASS` as its first line, then about a thousand lines of raw output as evidence — scroll back up to read that first line. Exit 0.

### STACK-09 — Itanium ABI mangling and demangling (F8)

```bash
cd /atp
cd coretrace-stack-analyzer
./build/stack_usage_analyzer test/test.cpp | head -5
./build/stack_usage_analyzer test/test.cpp --demangle | head -5
./build/stack_usage_analyzer test/test.cpp --format=json | python3 -c "import sys,json;print(json.load(sys.stdin)['functions'][0]['name'])"
python3 -B BTP-STACK-ANALYZER-F8.py
```

**Attendu :** Default human output shows both forms on one line, e.g. `_ZN12demo_symbols17scalar_parametersEidc demo_symbols::scalar_parameters(int, double, char)`. With `--demangle` only the readable signature remains. JSON prints the raw symbol `_ZN12demo_symbols17scalar_parametersEidc`. The F8 proof prints `[F8] BTP-STACK-ANALYZER-F8: PASS` as its first line, then the mangled and demangled symbols it checked, and exits 0.

### STACK-10 — Clean source produces no diagnostic

```bash
cd /atp
cd coretrace-stack-analyzer
./build/stack_usage_analyzer test/no-error/basic-main.c --warnings-only
```

**Attendu :** Output is exactly `Mode: IR` followed by `Diagnostics summary: info=0, warning=0, error=0`. No warning, no error, exit code 0.

### STACK-11 — False-positive regression corpus

```bash
cd /atp
cd coretrace-stack-analyzer
grep -v '^#' ../datasets/stack-no-false-positive.txt | grep -v '^$' | while read f; do out=$(./build/stack_usage_analyzer "$f" --warnings-only 2>&1); rc=$?; n=$(printf '%s\n' "$out" | grep -c '!!'); echo "$n exit=$rc $f"; done
```

**Attendu :** 15 lines, every one starting with `0 exit=0`. A line starting with a non-zero count is a false-positive regression; a line showing a non-zero exit is a file the analyzer could not analyse. Either way report the file name in Feedback. (The rest of test/false-positive-repro/ is not checked here: those fixtures reproduce one false positive while still containing a real defect, so they legitimately emit diagnostics. STACK-12 checks them against the expectations embedded in each file.)

### STACK-12 — Full regression suite, including the SMT pass

```bash
cd /atp
cd coretrace-stack-analyzer
python3 -u run_test.py --jobs 8
```

**Attendu :** The run ends with `All tests passed.` and `Passed N/N tests.` with no failure — 2916/2916 at the revision under test. Exit code 0. The report includes `(smt-z3)` lines, proving the SMT pass ran and did not change the verdicts.

### STACK-13 — CI adapter: artifacts and policy gate

```bash
cd /atp
cd coretrace-stack-analyzer
mkdir -p /tmp/atp-artifacts
python3 scripts/ci/run_code_analysis.py --analyzer ./build/stack_usage_analyzer --fail-on error --json-out /tmp/atp-artifacts/bad.json --sarif-out /tmp/atp-artifacts/bad.sarif test/local-storage/c/stack-exhaustion-large-frame.c; echo "exit=$?"
python3 scripts/ci/run_code_analysis.py --analyzer ./build/stack_usage_analyzer --fail-on error --json-out /tmp/atp-artifacts/ok.json --sarif-out /tmp/atp-artifacts/ok.sarif test/no-error/basic-main.c; echo "exit=$?"
```

**Attendu :** First run prints `Findings summary: errors=1, warnings=1, infos=0`, then `CI gate failed (fail-on=error).` and `exit=1`. Second run prints `exit=0`. All four artifact files exist and the two .sarif files parse as JSON.

### STACK-14 — Error handling on invalid input

```bash
cd /atp
cd coretrace-stack-analyzer
./build/stack_usage_analyzer /tmp/does-not-exist.c; echo "exit=$?"
./build/stack_usage_analyzer --not-a-real-option test/no-error/basic-main.c; echo "exit=$?"
./build/stack_usage_analyzer --help | head -3
```

**Attendu :** The missing file prints `Compilation failed:` followed by `error reading '/tmp/does-not-exist.c': No such file or directory` and `Failed to analyze: ...`, then `exit=1`. The bad option prints `Unknown option: --not-a-real-option`, then `exit=1`. Neither segfaults, prints a stack trace or hangs. `--help` prints the banner `Stack Usage Analyzer - static stack usage analysis for LLVM IR/bitcode`.

### STACK-15 — ABI analysis mode (F1)

```bash
cd /atp
cd coretrace-stack-analyzer
./build/stack_usage_analyzer test/local-storage/c/stack-callee-caller.c --format=json | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['meta']['mode'],[(f['name'],f['localStack']) for f in d['functions']])"
./build/stack_usage_analyzer test/local-storage/c/stack-callee-caller.c --mode=abi --format=json | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['meta']['mode'],[(f['name'],f['localStack']) for f in d['functions']])"
```

**Attendu :** The first line starts with `IR` and reports `bar` and `mano` with `localStack` 0. The second starts with `ABI` and reports the same two functions with `localStack` 32 — the ABI mode adds the caller-saved area the IR view does not model. `foo` is identical in both. A run where both modes print the same numbers means `--mode` was ignored.

### STACK-16 — Whole-project analysis from compile_commands.json

```bash
cd /atp
cd coretrace-stack-analyzer
./build/stack_usage_analyzer --compile-commands=build/compile_commands.json --analysis-profile=fast --exclude-dir=build/_deps --warnings-only
```

**Attendu :** The run ends with a single aggregate line of the form `Total diagnostics summary: info=0, warning=<n>, error=0 (across <m> files)` — observed `warning=6` across 53 files. Those two numbers depend on the platform and are not the check. What must hold: several dozen files analysed in one invocation, `error=0` (the project keeps its own CI gate green), and no line starting with `Failed to analyze`.

### STACK-17 — Security diagnostics across the fifteen categories of the corpus

```bash
cd /atp
cd coretrace-stack-analyzer
for f in test/security/*/*.c; do printf '%s: ' "${f#test/security/}"; ./build/stack_usage_analyzer "$f" --resource-model=models/resource-lifetime/generic.txt --format=json 2>/dev/null | python3 -c "import sys,json;print(' '.join(sorted({d['ruleId'] for d in json.load(sys.stdin)['diagnostics'] if d['severity']!='INFO'})))"; done
```

**Attendu :** 24 lines, one per file, each giving the rules reported as warnings or errors. Every category shows its own rule: buffer-overflow `StackBufferOverflow.EveryRun`; command-injection `CommandInjection.NonLiteralCommand`; format-string `FormatString.NonLiteral`; integer-overflow `IntegerOverflow.SignedArithmetic`; memory-leak `ResourceLifetime.MissingRelease`; null-dereference `NullPointerDereference`; oob-read `OutOfBoundsRead.HeapIndex` or `OutOfBoundsRead.MissingNullTerminator`; sizeof-pitfall `SizeofPitfall`; stack-escape `StackPointerEscape`; toctou `TOCTOU.PathCheckThenUse`; type-confusion `TypeConfusion.IncompatibleStructView`; uninitialized `UninitializedLocalRead`; unsafe-functions `UnsafeFunction.DeprecatedGets`; use-after-free `ResourceLifetime.UseAfterRelease`; variadic-mismatch `VariadicFormatMismatch`. Two oob-read files, heap-index-masked.c and heap-index-modulo.c, are safe variants and print nothing after their name. A Python `Traceback` on a line means the analyzer could not analyse that file. The `--resource-model` option is what makes the memory-leak and use-after-free categories report.

## CONC — analyseur de concurrence (coretrace-concurrency-analyzer)

### CONC-01 — Data race on an unsynchronised global (F12)

```bash
cd /atp
cd coretrace-concurrency-analyzer
./build/coretrace_concurrency_analyzer tests/fixtures/concurrency/data-race/data_race_basic.c --analyze --format=human
```

**Attendu :** One diagnostic with `severity: ERROR`, `ruleId: DataRaceGlobal`, `cwe: CWE-362`, `symbol: shared_counter`, the message `unsynchronized concurrent access to global 'shared_counter'`, a `first access` and a `conflicting access` note each carrying file:line:column, and `Diagnostics summary: info=0, warning=0, error=1`.

### CONC-02 — Thread handle never joined or detached (F12)

```bash
cd /atp
cd coretrace-concurrency-analyzer
./build/coretrace_concurrency_analyzer tests/fixtures/concurrency/missing-join/missing_join_basic.c --analyze --rules=missing-join
./build/coretrace_concurrency_analyzer tests/fixtures/concurrency/missing-join/cpp_std_thread_missing_join.cpp --analyze --rules=missing-join
./build/coretrace_concurrency_analyzer tests/fixtures/concurrency/missing-join/pthread_join_all_no_missing_join.c --analyze --rules=missing-join
```

**Attendu :** The first two runs report `ruleId: MissingJoin` with `thread handle is not joined or detached before scope exit`; the pthread case shows `handle kind: pthread` and `lifecycle summary: creates=1, joins=0, detaches=0`. The third run, where every thread is joined, reports `info=0, warning=0, error=0`.

### CONC-03 — Deadlock through lock-order inversion (F12)

```bash
cd /atp
cd coretrace-concurrency-analyzer
./build/coretrace_concurrency_analyzer tests/fixtures/concurrency/deadlock/deadlock_basic.c --analyze --rules=deadlock-lock-order
```

**Attendu :** `severity: ERROR`, `ruleId: DeadlockLockOrder`, `cwe: CWE-833`, message `potential deadlock caused by inconsistent lock acquisition order`, a `first order: acquire 'lockB' while holding 'lockA'` note and a `conflicting order: acquire 'lockA' while holding 'lockB'` note, and `error=1`.

### CONC-04 — Deadlock through a three-lock cycle (F12)

```bash
cd /atp
cd coretrace-concurrency-analyzer
./build/coretrace_concurrency_analyzer tests/fixtures/concurrency/deadlock/deadlock_three_lock_cycle.c --analyze --rules=deadlock-lock-order
```

**Attendu :** One error reading `potential deadlock caused by a cycle of 3 lock acquisitions`, listing the three edges first_lock->second_lock, second_lock->third_lock and third_lock->first_lock, and `error=1`.

### CONC-05 — No false positive on correctly synchronised code (F12)

```bash
cd /atp
cd coretrace-concurrency-analyzer
n=0; bad=0; while read f; do n=$((n+1)); s=$(./build/coretrace_concurrency_analyzer "$f" --analyze 2>&1 | tail -1); case "$s" in *"info=0, warning=0, error=0"*) ;; *) bad=$((bad+1)); echo "BAD $s | $f";; esac; done < <(grep -v '^#' ../datasets/conc-no-false-positive.txt | grep -v '^$'); echo "checked=$n bad=$bad"
./build/coretrace_concurrency_analyzer tests/fixtures/concurrency-cxx20/cpp_jthread_auto_join_no_missing_join.cpp --analyze -- -std=c++20 | tail -1
```

**Attendu :** The loop prints `checked=28 bad=0` and no `BAD` line. Each `BAD` line is a false positive, or a file that could not be analysed: report the file name in Feedback. The C++20 jthread case prints `Diagnostics summary: info=0, warning=0, error=0` — a jthread joins in its destructor, so it must not be reported as a missing join. (The `-- -std=c++20` suffix is required: without it clang defaults to an older standard and the fixture fails to compile.)

### CONC-06 — Rule selection (F12)

```bash
cd /atp
cd coretrace-concurrency-analyzer
./build/coretrace_concurrency_analyzer tests/fixtures/concurrency/deadlock/deadlock_basic.c --analyze --rules=data-race | tail -1
./build/coretrace_concurrency_analyzer tests/fixtures/concurrency/deadlock/deadlock_basic.c --analyze --rules=deadlock-lock-order | tail -1
```

**Attendu :** With `--rules=data-race` the deadlock fixture reports `info=0, warning=0, error=0` — the deadlock checker did not run. With `--rules=deadlock-lock-order` the same file reports `error=1`.

### CONC-07 — Human, JSON and SARIF reporting (F12)

```bash
cd /atp
cd coretrace-concurrency-analyzer
F=tests/fixtures/concurrency/data-race/data_race_basic.c
./build/coretrace_concurrency_analyzer $F --analyze --format=json | python3 -m json.tool > /dev/null && echo JSON_OK
./build/coretrace_concurrency_analyzer $F --analyze --format=json | python3 -c "import sys,json;d=json.load(sys.stdin)['diagnostics'][0];print(d['ruleId'],d['cwe'],d['confidence'],sorted(d['details']))"
./build/coretrace_concurrency_analyzer $F --analyze --format=sarif > /tmp/conc07.sarif
python3 -c "import json;d=json.load(open('/tmp/conc07.sarif'));r=d['runs'][0];print(r['tool']['driver']['name'],len(r['results']),r['results'][0]['ruleId'])"
```

**Attendu :** `JSON_OK` is printed. Step 4 prints `DataRaceGlobal CWE-362 HIGH ['message', 'notes', 'properties']`: the JSON diagnostic carries its rule, CWE, confidence, notes and properties. The last command prints `coretrace-concurrency-analyzer 1 DataRaceGlobal`: the SARIF report holds the same single diagnostic.

### CONC-08 — Unit, architecture and golden-output test suites (F12)

```bash
cd /atp
cd coretrace-concurrency-analyzer
ctest --test-dir build --output-on-failure
CORETRACE_ANALYZER_BIN=./build/coretrace_concurrency_analyzer python3 -m pytest tests/integration/cli/test_human_output_golden.py -q
```

**Attendu :** CTest prints `100% tests passed, 0 tests failed out of 20`. pytest prints `10 passed`; each fixture matches its embedded EXPECT-HUMAN-DIAGNOSTICS block. Do NOT run the whole tests/integration/cli directory: test_analyzer.py requires the separate coretrace-testkit package.

### CONC-09 — Error handling on invalid input (F12)

```bash
cd /atp
cd coretrace-concurrency-analyzer
./build/coretrace_concurrency_analyzer /tmp/does-not-exist.c --analyze; echo "exit=$?"
./build/coretrace_concurrency_analyzer tests/fixtures/invalid.c --analyze; echo "exit=$?"
```

**Attendu :** The missing file yields `ruleId: CompilerDiagnostic` and the note `validate_input: input_file_does_not_exist: input file does not exist (/tmp/does-not-exist.c)`, then `exit=1`. The invalid source yields the clang parse errors and `exit=1`. Neither run crashes.

### CONC-10 — Public C++ API through an external consumer (F12)

```bash
cd /atp
cd coretrace-concurrency-analyzer
P=$(llvm-config --prefix); D=$PWD/build/_deps; cmake -S extern-project -B extern-project/build -G Ninja -DFETCHCONTENT_SOURCE_DIR_CC=$D/cc-src -DFETCHCONTENT_SOURCE_DIR_CORETRACE_LOGGER=$D/coretrace_logger-src -DLLVM_DIR=$P/lib/cmake/llvm -DClang_DIR=$P/lib/cmake/clang -DCLANG_EXECUTABLE=$P/bin/clang -DCLANG_RESOURCE_DIR=$($P/bin/clang -print-resource-dir)
cmake --build extern-project/build -j8
./extern-project/build/concurrency_consumer tests/fixtures/concurrency/data-race/data_race_basic.c
```

**Attendu :** Step 2 prints `-- Using local concurrency analyzer source` and ends with `-- Build files have been written to: /atp/coretrace-concurrency-analyzer/extern-project/build`. Step 3 compiles and links without error. Step 4 prints `Consumer compilation succeeded in bc mode, payload=<n> bytes` (4524 observed): a separate CMake project linked the analyzer library and compiled a source through its public API.

### CONC-11 — The eight other concurrency rules (F12)

```bash
cd /atp
cd coretrace-concurrency-analyzer
./build/coretrace_concurrency_analyzer tests/fixtures/concurrency/condition-variable/condition_variable_spurious.c --analyze --rules=condition-wait | grep -E "ruleId|summary"
./build/coretrace_concurrency_analyzer tests/fixtures/concurrency/process/fork_after_thread_creation.c --analyze --rules=fork-after-thread | grep -E "ruleId|summary"
./build/coretrace_concurrency_analyzer tests/fixtures/concurrency/process/fork_without_wait.c --analyze --rules=unreaped-child | grep -E "ruleId|summary"
./build/coretrace_concurrency_analyzer tests/fixtures/concurrency/missing-join/missing_join_multiple.c --analyze --rules=thread-arg-escape | grep -E "ruleId|summary"
./build/coretrace_concurrency_analyzer tests/fixtures/concurrency/signal-handler/signal_mutex_deadlock.c --analyze --rules=unsafe-signal-handler | grep -E "ruleId|summary"
./build/coretrace_concurrency_analyzer tests/fixtures/concurrency/atomic-ordering/publish_relaxed_load.c --analyze --rules=weak-publication | grep -E "ruleId|summary"
./build/coretrace_concurrency_analyzer tests/fixtures/concurrency/use-after-free/use_after_free_callback.c --analyze --rules=thread-arg-freed | grep -E "ruleId|summary"
./build/coretrace_concurrency_analyzer tests/fixtures/concurrency/thread-local/c_tls_dangling_ptr.c --analyze --rules=thread-local-escape | grep -E "ruleId|summary"
```

**Attendu :** Each command prints one `ruleId:` line and one summary line. In order: `ruleId: ConditionWaitWithoutPredicate`, `ruleId: ForkAfterThreadCreation`, `ruleId: UnreapedChildProcess`, `ruleId: ThreadArgumentEscapesFrame`, `ruleId: UnsafeSignalHandler`, `ruleId: WeakPublicationOrdering`, `ruleId: ThreadArgumentFreedEarly`, `ruleId: ThreadLocalOutlivesThread`. The summary is `Diagnostics summary: info=0, warning=0, error=1` for six of them, and `Diagnostics summary: info=0, warning=1, error=0` for the third (unreaped-child) and the sixth (weak-publication), which are warnings.

## RUN — analyseur runtime (coretrace-runtime-analyzer)

### RUN-01 — Instrumented build, execution and event collection (F4)

```bash
cd /atp
cd coretrace-runtime-analyzer
python3 -B BTP-RUNTIME-ANALYZER_F4.py
```

**Attendu :** The script reports `instrumented_binary_generated=OK`, `instrumented_binary_executable=OK`, `coretrace_lines_collected=OK`, `entry_events_collected=OK`, `exit_events_collected=OK`, then `[F4] result=OK`, exit 0. The collection block shows `entry_events=2` and `exit_events=2`.

### RUN-02 — Heap buffer overflow detected at runtime (F11)

```bash
cd /atp
cd coretrace-runtime-analyzer
python3 -B BTP-RUNTIME-ANALYZER_F11.py --no-color
```

**Attendu :** Output contains `ct: heap-buffer-overflow WRITE of size 1` with an `access=...:18:15` line, an `alloc_site=...:6:63` line and `alloc_size=8`. Status lines `runtime_analyzer_exit_reports_finding=OK` (the analyzer exits 1 when it reports a finding), `heap_buffer_overflow_reported=OK`, `write_overflow_reported=OK`, `bounds_errors_collected=OK`, `program_continued_after_detection=OK`, then a final `PASS`. The script itself exits 0.

### RUN-05 — Batch mode over a test directory (F4)

```bash
cd /atp
cd coretrace-runtime-analyzer
mkdir -p /tmp/atp-rt-src && cp test/ct_alloc_basic.c test/ct_autofree_local.c test/ct_new_delete.cpp /tmp/atp-rt-src/
./build/runtime-analyzer --test-dir /tmp/atp-rt-src --output-dir /tmp/atp-rt-out; echo "exit=$?"
```

**Attendu :** The batch block reports `tests=3`, `compile_failures=0` and `runtime_failures=0`. Each source has a `[PASS]` line naming the generated binary and `exit_code=0`. Under each file the analyzer lists the `memory leak` warnings it found in that program. The command ends with `exit=1`: the analyzer itself exits 1 because it reports those leaks, even though each test program exits 0. That exit code is expected here, it is not a failure of the batch.

### RUN-07 — Instrumentation modules: trace, alloc, bounds (F3)

```bash
cd /atp
cd coretrace-runtime-analyzer
./build/runtime-analyzer -o /tmp/f3-trace -- --ct-modules=trace test/examples/fixtures/hello.c; echo "exit=$?"
./build/runtime-analyzer -o /tmp/f3-alloc -- --ct-modules=alloc test/ct_alloc_basic.c; echo "exit=$?"
./build/runtime-analyzer -o /tmp/f3-bounds -- --ct-modules=alloc,bounds test/findings/heap_overflow_write.c; echo "exit=$?"
```

**Attendu :** First run (trace): `entry_events=1`, `exit_events=1`, `allocation_events=0`, then `exit=0`. Second run (alloc): `entry_events=0`, `allocation_events=8`, a `memory leak of 24 bytes` warning, then `exit=1` — the analyzer exits 1 when it reports a finding. Third run (alloc and bounds): `bounds_errors=1` and `test/findings/heap_overflow_write.c:8:15: error: heap-buffer-overflow WRITE of size 4 [heap-buffer-overflow, CWE-122]`, then `exit=1`; its `exit_code=134` line is the instrumented program being stopped at the overflow. Each module leaves the counters of the others at zero.

### RUN-08 — Memory defects found at runtime (F11)

```bash
cd /atp
cd coretrace-runtime-analyzer
for f in test/findings/*.c; do out=$(./build/runtime-analyzer -o /tmp/atp-finding -- --ct-modules=alloc,bounds "$f" 2>&1); rc=$?; echo "$(basename "$f") exit=$rc $(printf '%s\n' "$out" | grep -E 'error:|warning:' | head -1)"; done
```

**Attendu :** Seven lines. `double_free.c exit=1` with `[double-free, CWE-415]`; `heap_overflow_read.c exit=1` with `READ of size 4 [heap-buffer-overflow, CWE-125]`; `heap_overflow_write.c exit=1` with `WRITE of size 4 [heap-buffer-overflow, CWE-122]`; `memory_leak.c exit=1` with `[memory-leak, CWE-401]`; `no_findings.c exit=0` with nothing after it; `stack_overflow_write.c exit=1` with `[stack-buffer-overflow, CWE-121]`; `use_after_free.c exit=1` with `[heap-use-after-free, CWE-416]`. The analyzer exits 1 when it reports a finding and 0 when it finds none.

### RUN-09 — Unit, API and command-line test suite

```bash
cd /atp
cd coretrace-runtime-analyzer
ctest --test-dir build --output-on-failure
```

**Attendu :** `100% tests passed, 0 tests failed out of 17`. Exit code 0.

## CORE — orchestrateur (coretrace)

### CORE-01 — CLI help and version

```bash
cd /atp
cd coretrace
./build/ctrace --help
./build/ctrace --version
```

**Attendu :** `--help` lists at least `--static`, `--dyn`, `--invoke`, `--input`, `--sarif-format`, `--config`, `--fail-on`, `--ipc` and `--jobs`, and ends with an Examples section. `--version` prints `ctrace v0.85.0-109-g7de854e`, the revision under test.

### CORE-05 — SARIF report file (F5)

```bash
cd /atp
cd coretrace
./build/ctrace --invoke ctrace_stack_analyzer --input tests/null_pointer.c --sarif-format --report-file /tmp/atp-core.sarif; echo "exit=$?"
python3 -c "import json;d=json.load(open('/tmp/atp-core.sarif'));print(sorted(d),d['runs'][0]['tool']['driver']['name'],len(d['runs'][0]['results']))"
```

**Attendu :** Step 2 ends with `Verdict: info=0, warning=1, error=1, fail-on=error (exit code 2)` and `exit=2`: the analysed file holds an error-level defect, and 2 is the exit code ctrace gives a CI job in that case, not a failure of the scenario. Step 3 prints `['$schema', 'runs', 'version'] ctrace_stack_analyzer 2`: the report is a SARIF document with its three top-level keys, and it carries the two findings.

### CORE-06 — HTTP server mode (F9)

```bash
cd /atp
cd coretrace
./build/ctrace --ipc serve --serve-host 127.0.0.1 --serve-port 8099 --shutdown-token atp-secret &
sleep 2
curl -s -X POST http://127.0.0.1:8099/api -H 'Content-Type: application/json' -d '{"proto":"coretrace-1.0","id":1,"type":"request","method":"run_analysis","params":{"input":["./tests/null_pointer.c"],"invoke":["ctrace_stack_analyzer"],"static_analysis":false,"dynamic_analysis":false,"async":false}}'
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8099/shutdown -H 'Authorization: Bearer atp-secret'
```

**Attendu :** The /api call returns JSON with `"status":"ok"`, `"proto":"coretrace-1.0"`, `"id":1`, an `"invoked_tools":["ctrace_stack_analyzer"]` field and a `"diagnostics_summary_total"` object. The shutdown call prints `202` and the background server exits.

### CORE-07 — Server shutdown is token-protected (F9)

```bash
cd /atp
cd coretrace
./build/ctrace --ipc serve --serve-host 127.0.0.1 --serve-port 8098 --shutdown-token atp-secret &
sleep 2
curl -s -o /dev/null -w 'no-token=%{http_code}\n' -X POST http://127.0.0.1:8098/shutdown
curl -s -o /dev/null -w 'wrong-token=%{http_code}\n' -X POST http://127.0.0.1:8098/shutdown -H 'Authorization: Bearer wrong'
curl -s -o /dev/null -w 'good-token=%{http_code}\n' -X POST http://127.0.0.1:8098/shutdown -H 'Authorization: Bearer atp-secret'
```

**Attendu :** `no-token=403`, `wrong-token=403`, `good-token=202`. The server is still serving after the two rejected calls and stops only after the third.

### CORE-09 — Configuration file and CLI precedence

```bash
cd /atp
cd coretrace
python3 -c "import json;c=json.load(open('config/tool-config.json'));c['analysis']['invoke']=['ctrace_stack_analyzer'];c['output']['report_file']='/tmp/atp-from-config.json';json.dump(c,open('config/atp-prec.json','w'),indent=2)"
./build/ctrace --config config/atp-prec.json --input tests/null_pointer.c
ls -l /tmp/atp-from-config.json
./build/ctrace --config config/atp-prec.json --input tests/null_pointer.c --report-file /tmp/atp-from-cli.json
ls -l /tmp/atp-from-cli.json
rm -f config/atp-prec.json
```

**Attendu :** The first run writes /tmp/atp-from-config.json (path taken from the config file). The second writes /tmp/atp-from-cli.json, showing `--report-file` overrides the config. Both `ls -l` lines show an existing file, and both runs print a JSON report containing a `diagnosticsSummary` object. Each run ends with `Verdict: info=0, warning=1, error=1, fail-on=error (exit code 2)`: the analysed file holds an error-level defect, which is expected here.

### CORE-10 — Orchestrator test suite

```bash
cd /atp
cd coretrace
ctest --test-dir build --output-on-failure
```

**Attendu :** `100% tests passed, 0 tests failed out of 99`. Exit code 0.

### CORE-11 — Parallel tool execution (F7)

```bash
cd /atp
cd coretrace
python3 tests/BTP-STACK-ANALYZER-F7 --ctrace-bin ./build/ctrace --iterations 1 --warmups 0 --min-speedup-ratio 0; echo "exit=$?"
```

**Attendu :** The script prints `sync model: sequential CoreTrace tool invocations with -j1`, `async model: parallel CoreTrace tool invocations with -j4`, a `speedup:` line, and a `diagnostics:` line whose `"async"` and `"sync"` entries hold the same counts for `cppcheck` and `ctrace_stack_analyzer`. It ends with `exit=0`: the script exits non-zero when the two modes disagree. The speed-up value depends on the machine and is not the check.

### CORE-12 — Code style check on the four repositories (F6)

```bash
cd /atp
(cd coretrace && ./scripts/format-check.sh); echo "exit=$?"
(cd coretrace-stack-analyzer && ./scripts/format-check.sh); echo "exit=$?"
(cd coretrace-concurrency-analyzer && ./scripts/format-check.sh); echo "exit=$?"
(cd coretrace-runtime-analyzer && ./scripts/format-check.sh); echo "exit=$?"
```

**Attendu :** Each of the four commands prints `Checking formatting on <n> ... files...` (107, 637, 106 and 24 files), then `Formatting is clean.` and `exit=0`.

### CORE-13 — Several analyzers in one run, one merged verdict

```bash
cd /atp
cd coretrace
./build/ctrace --invoke ctrace_stack_analyzer,coretrace-concurrency-analyzer --input ../coretrace-concurrency-analyzer/tests/fixtures/concurrency/data-race/data_race_basic.c --report-file /tmp/atp-multi.json; echo "exit=$?"
```

**Attendu :** The log shows both tools running: `Running coretrace-concurrency-analyzer on 1 file(s)` and `Running CoreTrace Stack Analyzer on`. Each reports its own summary: `(coretrace-concurrency-analyzer) Diagnostics summary: info=0, warning=0, error=1` and `(ctrace_stack_analyzer) Diagnostics summary: info=1, warning=2, error=0`. The last line adds them up: `Verdict: info=1, warning=2, error=1, fail-on=error (exit code 2)`, then `exit=2` — the data race is an error-level finding.

## Signaler une anomalie

Une issue GitHub par anomalie, dans le dépôt indiqué par la clé du scénario
(STACK, CONC, RUN : le dépôt de l'analyseur ; CORE et ENV : `coretrace`), avec
la clé dans le titre, par exemple `[STACK-05] index off by one not reported`.
Joignez la commande exacte, la sortie complète et le résultat de :

```bash
./atp.sh versions       # sur votre machine ; ou : cat /atp/VERSIONS dans le conteneur
```
