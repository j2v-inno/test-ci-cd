#!/usr/bin/env bash
# Installs a self-hosted GitHub Actions runner on this host (Linux x64) and
# registers it against the repo as a systemd service.
#
# Usage:
#   ./setup-runner-ec2.sh <REGISTRATION_TOKEN> [<RUNNER_NAME>]
#
# Generate a registration token at:
#   https://github.com/j2v-inno/test-ci-cd/settings/actions/runners/new
# (Settings -> Actions -> Runners -> New self-hosted runner. Copy the value
# that follows --token in the suggested ./config.sh command. The token expires
# in ~1 hour; only used once during registration.)

set -euo pipefail

REPO_URL="https://github.com/j2v-inno/test-ci-cd"
RUNNER_LABELS="self-hosted,linux,rnd-ec2"
RUNNER_DIR="${HOME}/actions-runner"

TOKEN="${1:-${RUNNER_TOKEN:-}}"
RUNNER_NAME="${2:-$(hostname)}"

if [[ -z "${TOKEN}" ]]; then
  echo "ERROR: missing registration token." >&2
  echo "Usage: $0 <REGISTRATION_TOKEN> [<RUNNER_NAME>]" >&2
  echo "Get a token at: ${REPO_URL}/settings/actions/runners/new" >&2
  exit 1
fi

echo "Resolving latest actions/runner release..."
RUNNER_VERSION="$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest \
  | grep -Po '"tag_name":\s*"v\K[^"]+')"
echo "Latest runner version: ${RUNNER_VERSION}"

mkdir -p "${RUNNER_DIR}"
cd "${RUNNER_DIR}"

TARBALL="actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
if [[ ! -f "${TARBALL}" ]]; then
  echo "Downloading ${TARBALL}..."
  curl -fsSL -o "${TARBALL}" \
    "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${TARBALL}"
fi

if [[ ! -f config.sh ]]; then
  echo "Extracting runner..."
  tar xzf "${TARBALL}"
fi

# Runner must be able to talk to the Docker daemon
if ! id -nG "$(whoami)" | grep -qw docker; then
  echo "Adding $(whoami) to the docker group (group change applies to the systemd service)..."
  sudo usermod -aG docker "$(whoami)"
fi

if [[ ! -f .runner ]]; then
  echo "Configuring runner against ${REPO_URL}..."
  ./config.sh \
    --url "${REPO_URL}" \
    --token "${TOKEN}" \
    --name "${RUNNER_NAME}" \
    --labels "${RUNNER_LABELS}" \
    --unattended \
    --replace
else
  echo ".runner already exists; skipping config (delete ${RUNNER_DIR}/.runner to re-register)."
fi

if ! ls /etc/systemd/system/actions.runner.*.service >/dev/null 2>&1; then
  echo "Installing systemd service..."
  sudo ./svc.sh install "$(whoami)"
  sudo ./svc.sh start
else
  echo "Service already installed; restarting..."
  sudo ./svc.sh stop || true
  sudo ./svc.sh start
fi

echo
echo "Runner installed and running."
echo "  Name:   ${RUNNER_NAME}"
echo "  Labels: ${RUNNER_LABELS}"
echo "  Dir:    ${RUNNER_DIR}"
echo
echo "Verify in GitHub: ${REPO_URL}/settings/actions/runners"
echo "Tail logs:        sudo journalctl -u 'actions.runner.*' -f"
echo "Service status:   sudo ./svc.sh status   (from ${RUNNER_DIR})"
