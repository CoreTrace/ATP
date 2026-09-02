# SPDX-License-Identifier: Apache-2.0
#
# CoreTrace Acceptance Test Plan — Linux test environment.
#
# One image holding the four CoreTrace tools already built, plus their test
# fixtures. Testers on macOS run the scenarios natively; testers who need the
# Linux behaviour run the exact same commands inside this image.
#
# The build recipes below mirror each repository's own CI job (see
# .github/workflows/ in each repo). When a repo changes its LLVM version or
# CMake flags, change them here too or this image stops reproducing CI.
#
# Build context is the ATP directory (the parent of docker/), because the image
# needs all four repositories.
#
#   docker build -f docker/Dockerfile -t coretrace-atp:latest .
#   docker run --rm -it coretrace-atp:latest

FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive
ARG LLVM_VERSION=20

# build-essential: libstdc++ headers the analyzers read from C++ fixtures.
# cppcheck: third-party static analyzer orchestrated by ctrace (--invoke).
# python3-pytest: concurrency analyzer golden-output suite.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        cmake \
        cppcheck \
        curl \
        git \
        gnupg \
        jq \
        lsb-release \
        ninja-build \
        python3 \
        python3-pytest \
        software-properties-common \
    && curl -fsSL https://apt.llvm.org/llvm.sh -o /tmp/llvm.sh \
    && chmod +x /tmp/llvm.sh \
    && /tmp/llvm.sh ${LLVM_VERSION} \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        clang-${LLVM_VERSION} \
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

# Each repository is copied and built separately so that editing one does not
# invalidate the cached build of the other three.

# --- coretrace-stack-analyzer -------------------------------------------------
COPY coretrace-stack-analyzer /atp/coretrace-stack-analyzer
RUN cmake -S /atp/coretrace-stack-analyzer -B /atp/coretrace-stack-analyzer/build -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
        -DLLVM_DIR="${LLVM_DIR}" \
        -DClang_DIR="${Clang_DIR}" \
        -DUSE_SHARED_LIB=OFF \
    && cmake --build /atp/coretrace-stack-analyzer/build -j"$(nproc)"

# --- coretrace-concurrency-analyzer -------------------------------------------
COPY coretrace-concurrency-analyzer /atp/coretrace-concurrency-analyzer
RUN cmake -S /atp/coretrace-concurrency-analyzer -B /atp/coretrace-concurrency-analyzer/build -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DLLVM_DIR="${LLVM_DIR}" \
        -DClang_DIR="${Clang_DIR}" \
        -DCLANG_EXECUTABLE="${CLANG_EXECUTABLE}" \
        -DCLANG_RESOURCE_DIR="$(${CLANG_EXECUTABLE} -print-resource-dir)" \
    && cmake --build /atp/coretrace-concurrency-analyzer/build -j"$(nproc)"

# --- coretrace-runtime-analyzer -----------------------------------------------
COPY coretrace-runtime-analyzer /atp/coretrace-runtime-analyzer
RUN cmake -S /atp/coretrace-runtime-analyzer -B /atp/coretrace-runtime-analyzer/build -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DLLVM_DIR="${LLVM_DIR}" \
        -DClang_DIR="${Clang_DIR}" \
        -DCLANG_LINK_CLANG_DYLIB=ON \
        -DLLVM_LINK_LLVM_DYLIB=ON \
        -DUSE_SHARED_LIB=OFF \
    && cmake --build /atp/coretrace-runtime-analyzer/build -j"$(nproc)"

# --- coretrace (orchestrator) -------------------------------------------------
# Fetches coretrace-stack-analyzer from GitHub at configure time, so this layer
# needs network access.
ARG CORETRACE_VERSION=dev
COPY coretrace /atp/coretrace
RUN cmake -S /atp/coretrace -B /atp/coretrace/build -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCORETRACE_VERSION_OVERRIDE="${CORETRACE_VERSION}" \
        -DPARSER_TYPE=CLI11 \
        -DUSE_THREAD_SANITIZER=OFF \
        -DUSE_ADDRESS_SANITIZER=OFF \
        -DLLVM_DIR="${LLVM_DIR}" \
        -DClang_DIR="${Clang_DIR}" \
    && cmake --build /atp/coretrace/build -j"$(nproc)"

# Scenarios run unprivileged: several concurrency CLI tests assert that an
# unreadable path fails, and root reads it regardless, so as root those tests
# report a false failure. uid 1000 is the `ubuntu` account of the base image.
RUN chown -R ubuntu:ubuntu /atp
USER ubuntu
ENV HOME=/home/ubuntu

WORKDIR /atp
CMD ["bash"]
