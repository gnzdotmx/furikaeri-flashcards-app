#!/usr/bin/env sh
set -eu

echo "Running npm audit (requires network)..."
npm audit --audit-level=high

