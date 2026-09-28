#!/bin/bash

# Deploy script

echo "[INFO] Discarding previous containers..."
docker compose --env-file .env -f docker/compose-deploy.yaml down --rmi local --remove-orphans -v

echo "[INFO] Building project..."
docker compose --env-file .env -f docker/compose-deploy.yaml build

echo "[INFO] Preparing services..."
docker compose --env-file .env -f docker/compose-deploy.yaml up -d

echo "[INFO] Services healthy."
