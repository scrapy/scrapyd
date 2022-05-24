#!/bin/sh

echo "Waiting for orchestrator..."

while ! nc -z $ORCHESTRATOR_IP $ORCHESTRATOR_PORT; do
  sleep 0.1
done

echo "Orchestrator started"

exec "$@"