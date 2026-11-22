#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Single entry point for the CoreTrace Acceptance Test Plan.
#
#   ./atp.sh build-linux    build the Linux test image (Docker, needs network)
#   ./atp.sh linux          open a shell inside the image, at /atp
#   ./atp.sh versions       print the revisions under test (paste it in every issue)
#
# The revisions under test are fixed in docker/Dockerfile: the image clones the
# four CoreTrace repositories itself, so nothing has to be cloned on the host.
#
#   ATP_JOBS=4 ./atp.sh build-linux    fewer parallel jobs (less memory, slower)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${ATP_IMAGE:-coretrace-atp:latest}"

die() { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }
info() { printf '\033[36m==>\033[0m %s\n' "$*"; }

need_docker() {
    command -v docker >/dev/null 2>&1 || die "docker not found: install Docker Desktop or Docker Engine"
    docker info >/dev/null 2>&1 || die "the Docker daemon is not running: start Docker, then retry"
}

need_image() {
    need_docker
    docker image inspect "${IMAGE}" >/dev/null 2>&1 || die "image ${IMAGE} not found. Run: ./atp.sh build-linux"
}

cmd_build_linux() {
    need_docker
    info "building ${IMAGE} (needs network access)"
    docker build ${ATP_PLATFORM:+--platform "${ATP_PLATFORM}"} \
        ${ATP_JOBS:+--build-arg "JOBS=${ATP_JOBS}"} \
        -f "${ROOT}/docker/Dockerfile" -t "${IMAGE}" "${ROOT}"
    info "done — open a shell with: ./atp.sh linux"
}

cmd_linux() {
    need_image
    # --init gives the container a real init process: it reaps the processes a
    # killed tool leaves behind, which the orchestrator's own tests rely on
    # (CORE-10 fails two of them without it).
    exec docker run --rm -it --init ${ATP_PLATFORM:+--platform "${ATP_PLATFORM}"} \
        -w /atp "${IMAGE}" "${@:-bash}"
}

cmd_versions() {
    need_image
    docker run --rm ${ATP_PLATFORM:+--platform "${ATP_PLATFORM}"} "${IMAGE}" cat /atp/VERSIONS
}

case "${1:-}" in
    build-linux)  cmd_build_linux ;;
    linux)        shift; cmd_linux "$@" ;;
    versions)     cmd_versions ;;
    *) sed -n '4,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
