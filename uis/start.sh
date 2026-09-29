#!/bin/sh
set -eu

npm --prefix /app/uis/website run dev -- --host 0.0.0.0 &
website_pid=$!
npm --prefix /app/uis/backoffice run dev -- --host 0.0.0.0 &
backoffice_pid=$!

trap 'kill "$website_pid" "$backoffice_pid" 2>/dev/null || true' INT TERM EXIT
wait "$website_pid" "$backoffice_pid"