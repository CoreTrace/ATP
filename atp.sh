#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Single entry point for the CoreTrace Acceptance Test Plan.
#
# The four analyzers each have their own build recipe; a tester should not have
# to know four of them. This script exposes one command per platform and leaves
# the scenarios themselves identical on both.
#
#   ./atp.sh doctor         check host prerequisites
#   ./atp.sh build-macos    build the four tools natively (macOS, Homebrew LLVM 20)
#   ./atp.sh build-linux    build the Linux test image (Docker)
#   ./atp.sh linux          open a shell inside the Linux image, at /atp
#   ./atp.sh versions       print the version of every built tool

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${ATP_IMAGE:-coretrace-atp:latest}"
REPOS=(coretrace-stack-analyzer coretrace-concurrency-analyzer coretrace-runtime-analyzer coretrace)

die() { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }
info() { printf '\033[36m==>\033[0m %s\n' "$*"; }
ok() { printf '\033[32mOK\033[0m   %s\n' "$*"; }
no() { printf '\033[31mNO\033[0m   %s\n' "$*"; }

# --- prerequisites -----------------------------------------------------------

llvm_prefix() {
    # Linux ships LLVM under a versioned prefix, Homebrew under a keg. Both
    # provide llvm-config, which is the only thing CMake actually needs.
    if [ -n "${LLVM_PREFIX:-}" ]; then
        printf '%s' "${LLVM_PREFIX}"
    elif command -v brew >/dev/null 2>&1 && brew --prefix llvm@20 >/dev/null 2>&1; then
        brew --prefix llvm@20
    elif [ -d /usr/lib/llvm-20 ]; then
        printf '%s' /usr/lib/llvm-20
    else
        return 1
    fi
}

cmd_doctor() {
    local failed=0
    for tool in cmake ninja git python3; do
        if command -v "${tool}" >/dev/null 2>&1; then ok "${tool}"; else no "${tool} (missing)"; failed=1; fi
    done
    if command -v cppcheck >/dev/null 2>&1; then
        ok "cppcheck"
    else
        no "cppcheck (missing — scenario CORE-04 will fail)"
    fi
    if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        ok "docker (running)"
    else
        no "docker (missing or not running — Linux scenarios unavailable)"
    fi
    if prefix="$(llvm_prefix)"; then
        ok "LLVM 20 at ${prefix}"
    else
        no "LLVM 20 (missing — run: brew install llvm@20)"
        failed=1
    fi
    [ "${failed}" -eq 0 ] || die "missing prerequisites, see README.md"
    info "host is ready"
}

# --- macOS native build ------------------------------------------------------

cmd_build_macos() {
    local prefix
    prefix="$(llvm_prefix)" || die "LLVM 20 not found. Run: brew install llvm@20 cmake ninja"
    local llvm_dir="${prefix}/lib/cmake/llvm"
    local clang_dir="${prefix}/lib/cmake/clang"
    local clang_exe="${prefix}/bin/clang"
    local resource_dir
    resource_dir="$("${clang_exe}" -print-resource-dir)"

    for repo in "${REPOS[@]}"; do
        [ -d "${ROOT}/${repo}" ] || die "missing repository: ${repo}"
    done

    info "coretrace-stack-analyzer"
    cmake -S "${ROOT}/coretrace-stack-analyzer" -B "${ROOT}/coretrace-stack-analyzer/build" -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
        -DLLVM_DIR="${llvm_dir}" -DClang_DIR="${clang_dir}" -DUSE_SHARED_LIB=OFF
    cmake --build "${ROOT}/coretrace-stack-analyzer/build" -j"$(sysctl -n hw.ncpu 2>/dev/null || nproc)"

    info "coretrace-concurrency-analyzer"
    cmake -S "${ROOT}/coretrace-concurrency-analyzer" -B "${ROOT}/coretrace-concurrency-analyzer/build" -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DLLVM_DIR="${llvm_dir}" -DClang_DIR="${clang_dir}" \
        -DCLANG_EXECUTABLE="${clang_exe}" -DCLANG_RESOURCE_DIR="${resource_dir}"
    cmake --build "${ROOT}/coretrace-concurrency-analyzer/build" -j"$(sysctl -n hw.ncpu 2>/dev/null || nproc)"

    info "coretrace-runtime-analyzer"
    cmake -S "${ROOT}/coretrace-runtime-analyzer" -B "${ROOT}/coretrace-runtime-analyzer/build" -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DLLVM_DIR="${llvm_dir}" -DClang_DIR="${clang_dir}" -DUSE_SHARED_LIB=OFF
    cmake --build "${ROOT}/coretrace-runtime-analyzer/build" -j"$(sysctl -n hw.ncpu 2>/dev/null || nproc)"

    info "coretrace"
    cmake -S "${ROOT}/coretrace" -B "${ROOT}/coretrace/build" -G Ninja \
        -DCMAKE_BUILD_TYPE=Release -DPARSER_TYPE=CLI11 \
        -DUSE_THREAD_SANITIZER=OFF -DUSE_ADDRESS_SANITIZER=OFF \
        -DLLVM_DIR="${llvm_dir}" -DClang_DIR="${clang_dir}"
    cmake --build "${ROOT}/coretrace/build" -j"$(sysctl -n hw.ncpu 2>/dev/null || nproc)"

    cmd_versions
}

# --- Linux image -------------------------------------------------------------

cmd_build_linux() {
    command -v docker >/dev/null 2>&1 || die "docker not found"
    docker info >/dev/null 2>&1 || die "docker daemon is not running"
    # .dockerignore strips .git, so ctrace cannot resolve its own version
    # inside the image; hand it the tag the host sees.
    local version
    version="$(git -C "${ROOT}/coretrace" describe --tags --always 2>/dev/null || echo dev)"
    info "building ${IMAGE} (30-60 min on first run, needs network access)"
    docker build ${ATP_PLATFORM:+--platform "${ATP_PLATFORM}"} \
        --build-arg "CORETRACE_VERSION=${version}" \
        -f "${ROOT}/docker/Dockerfile" -t "${IMAGE}" "${ROOT}"
    info "done — open a shell with: ./atp.sh linux"
}

cmd_linux() {
    docker image inspect "${IMAGE}" >/dev/null 2>&1 || die "image ${IMAGE} not found. Run: ./atp.sh build-linux"
    # No bind mount: the image already holds the sources it was built from, so
    # a scenario cannot accidentally run against a macOS build tree.
    exec docker run --rm -it ${ATP_PLATFORM:+--platform "${ATP_PLATFORM}"} \
        -w /atp "${IMAGE}" "${@:-bash}"
}

# --- reporting ---------------------------------------------------------------

cmd_versions() {
    printf '%-38s %s\n' "coretrace" "$("${ROOT}/coretrace/build/ctrace" --version 2>/dev/null | head -1 || echo 'not built')"
    for repo_bin in \
        "coretrace-stack-analyzer:coretrace-stack-analyzer/build/stack_usage_analyzer" \
        "coretrace-concurrency-analyzer:coretrace-concurrency-analyzer/build/coretrace_concurrency_analyzer" \
        "coretrace-runtime-analyzer:coretrace-runtime-analyzer/build/runtime-analyzer"; do
        name="${repo_bin%%:*}"; path="${ROOT}/${repo_bin#*:}"
        if [ -x "${path}" ]; then
            printf '%-38s %s\n' "${name}" "built ($(git -C "${ROOT}/${name}" describe --tags --always 2>/dev/null || echo 'unknown rev'))"
        else
            printf '%-38s %s\n' "${name}" "not built"
        fi
    done
}

case "${1:-}" in
    doctor)       cmd_doctor ;;
    build-macos)  cmd_build_macos ;;
    build-linux)  cmd_build_linux ;;
    linux)        shift; cmd_linux "$@" ;;
    versions)     cmd_versions ;;
    *) sed -n '4,14p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
