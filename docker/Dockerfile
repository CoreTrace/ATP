# SPDX-License-Identifier: Apache-2.0
#
# CoreTrace Acceptance Test Plan — Linux test environment.
#
# One image holding the four CoreTrace tools already built, plus their test
# fixtures. The image clones each repository itself, at the revision under
# test, so a tester needs nothing on the host but Docker.
#
# The build recipes below mirror each repository's own CI job (see
# .github/workflows/ in each repo). When a repo changes its LLVM version or
# CMake flags, change them here too or this image stops reproducing CI.
#
#   ./atp.sh build-linux
#   ./atp.sh linux

FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive
ARG LLVM_VERSION=20

# build-essential: libstdc++ headers the analyzers read from C++ fixtures.
# cppcheck, flawfinder: third-party analyzers orchestrated by ctrace (--invoke).
# libz3-dev, lld, pkg-config: stack analyzer SMT backend and link step.
# python3-pytest: concurrency analyzer golden-output suite.
# clang-format: the repositories' own style check (scripts/format-check.sh).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        cmake \
        cppcheck \
        curl \
        flawfinder \
        git \
        gnupg \
        jq \
        libz3-dev \
        lld \
        lsb-release \
        ninja-build \
        patchelf \
        pkg-config \
        python3 \
        python3-pytest \
        software-properties-common \
    && curl -fsSL https://apt.llvm.org/llvm.sh -o /tmp/llvm.sh \
    && chmod +x /tmp/llvm.sh \
    && /tmp/llvm.sh ${LLVM_VERSION} \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        clang-${LLVM_VERSION} \
        clang-format-${LLVM_VERSION} \
        libclang-${LLVM_VERSION}-dev \
        llvm-${LLVM_VERSION} \
        llvm-${LLVM_VERSION}-dev \
    && rm -f /tmp/llvm.sh \
    && rm -rf /var/lib/apt/lists/*

ENV LLVM_DIR=/usr/lib/llvm-20/lib/cmake/llvm \
    Clang_DIR=/usr/lib/llvm-20/lib/cmake/clang \
    CLANG_EXECUTABLE=/usr/bin/clang-20 \
    LD_LIBRARY_PATH=/usr/lib/llvm-20/lib \
    PATH=/usr/lib/llvm-20/bin:/usr/local/bin:/usr/bin:/bin

# Parallel build jobs. Empty means every core Docker has; ATP_JOBS=4 ./atp.sh
# build-linux lowers it on a machine short of memory.
ARG JOBS=""

# --- revisions under test -----------------------------------------------------
# The single source of truth for what the plan is run against. Each repository
# pins its own coretrace-compiler / coretrace-log version, fetched by CMake at
# configure time, so nothing else has to be fixed here. Every layer below needs
# network access.
ARG STACK_REF=588e8008df1bc6f125943b4c86262e08a8a3efde
ARG CONCURRENCY_REF=fe3327d4fcbf23660393de31627645cef3f75004
ARG RUNTIME_REF=dd659815097c9c0569c4ba9d24a34435ef719465
ARG CORETRACE_REF=7de854ef6a8cb92f84bdfc442fba7b75f084bb8f

# Each repository is cloned and built in its own layer so that moving one
# revision does not rebuild the other three.

# --- coretrace-stack-analyzer -------------------------------------------------
RUN git clone -q https://github.com/CoreTrace/coretrace-stack-analyzer.git /atp/coretrace-stack-analyzer \
    && git -C /atp/coretrace-stack-analyzer checkout -q --detach "${STACK_REF}" \
    && cmake -S /atp/coretrace-stack-analyzer -B /atp/coretrace-stack-analyzer/build -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
        -DLLVM_DIR="${LLVM_DIR}" \
        -DClang_DIR="${Clang_DIR}" \
        -DUSE_SHARED_LIB=OFF \
        -DCMAKE_EXE_LINKER_FLAGS=-fuse-ld=lld \
        -DCMAKE_SHARED_LINKER_FLAGS=-fuse-ld=lld \
    && cmake --build /atp/coretrace-stack-analyzer/build -j"${JOBS:-$(nproc)}"

# --- coretrace-concurrency-analyzer -------------------------------------------
RUN git clone -q https://github.com/CoreTrace/coretrace-concurrency-analyzer.git /atp/coretrace-concurrency-analyzer \
    && git -C /atp/coretrace-concurrency-analyzer checkout -q --detach "${CONCURRENCY_REF}" \
    && cmake -S /atp/coretrace-concurrency-analyzer -B /atp/coretrace-concurrency-analyzer/build -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DLLVM_DIR="${LLVM_DIR}" \
        -DClang_DIR="${Clang_DIR}" \
        -DCLANG_EXECUTABLE="${CLANG_EXECUTABLE}" \
        -DCLANG_RESOURCE_DIR="$(${CLANG_EXECUTABLE} -print-resource-dir)" \
    && cmake --build /atp/coretrace-concurrency-analyzer/build -j"${JOBS:-$(nproc)}"

# --- coretrace-runtime-analyzer -----------------------------------------------
RUN git clone -q https://github.com/CoreTrace/coretrace-runtime-analyzer.git /atp/coretrace-runtime-analyzer \
    && git -C /atp/coretrace-runtime-analyzer checkout -q --detach "${RUNTIME_REF}" \
    && cmake -S /atp/coretrace-runtime-analyzer -B /atp/coretrace-runtime-analyzer/build -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DLLVM_DIR="${LLVM_DIR}" \
        -DClang_DIR="${Clang_DIR}" \
    && cmake --build /atp/coretrace-runtime-analyzer/build -j"${JOBS:-$(nproc)}"

# --- coretrace (orchestrator) -------------------------------------------------
RUN git clone -q https://github.com/CoreTrace/coretrace.git /atp/coretrace \
    && git -C /atp/coretrace checkout -q --detach "${CORETRACE_REF}" \
    && cmake -S /atp/coretrace -B /atp/coretrace/build -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DUSE_THREAD_SANITIZER=OFF \
        -DUSE_ADDRESS_SANITIZER=OFF \
        -DLLVM_DIR="${LLVM_DIR}" \
        -DClang_DIR="${Clang_DIR}" \
    && cmake --build /atp/coretrace/build -j"${JOBS:-$(nproc)}"

# What the image was built from, quoted in every anomaly report
# (./atp.sh versions on the host, cat /atp/VERSIONS in the container).
RUN for r in coretrace coretrace-stack-analyzer coretrace-concurrency-analyzer coretrace-runtime-analyzer; do \
        printf '%-32s %-24s %s\n' "$r" "$(git -C /atp/$r describe --tags --always)" "$(git -C /atp/$r rev-parse HEAD)"; \
    done > /atp/VERSIONS

# Data and proof scripts referenced by the scenarios. Copied after the builds:
# editing them must not invalidate four expensive compile layers. The proof
# scripts sit at the root of the repository they exercise, where the scenarios
# call them.
COPY datasets /atp/datasets
COPY proofs/coretrace-stack-analyzer/ /atp/coretrace-stack-analyzer/
COPY proofs/coretrace-runtime-analyzer/ /atp/coretrace-runtime-analyzer/

# Scenarios run unprivileged: several concurrency CLI tests assert that an
# unreadable path fails, and root reads it regardless, so as root those tests
# report a false failure. uid 1000 is the `ubuntu` account of the base image.
RUN chown -R ubuntu:ubuntu /atp
USER ubuntu
ENV HOME=/home/ubuntu

WORKDIR /atp
CMD ["bash"]
