#!/usr/bin/env bash
set -euo pipefail

# Never remove containers from other projects.
docker compose up --build -d
printf 'City-Farm: http://localhost\nRabbitMQ: http://localhost:15672\n'
