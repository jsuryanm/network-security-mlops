#!/usr/bin/env bash
# Download the newest trained model from S3 into a folder, but only if the folder has none.
# The training pipeline uploads each run to s3://<bucket>/final_model/<timestamp>/.
#
# Usage: scripts/fetch_latest_model.sh <bucket> <dest-dir>
# Needs the AWS CLI and credentials (on EC2: the instance role) plus a region
# (AWS_DEFAULT_REGION).
set -euo pipefail

BUCKET="${1:?usage: fetch_latest_model.sh <bucket> <dest-dir>}"
DEST="${2:?usage: fetch_latest_model.sh <bucket> <dest-dir>}"

if [ -f "$DEST/model.pkl" ] && [ -f "$DEST/preprocessor.pkl" ]; then
  echo "Model already present in $DEST, nothing to do."
  exit 0
fi

# Folder names look like 11_25_2026_11_41_49 (month first), so sorting by name would
# pick the wrong run. Sort by upload time instead.
KEY="$(aws s3api list-objects-v2 --bucket "$BUCKET" --prefix final_model/ \
  --query 'sort_by((Contents || `[]`), &LastModified)[-1].Key' --output text)"

if [ -z "$KEY" ] || [ "$KEY" = "None" ]; then
  echo "WARNING: no model under s3://$BUCKET/final_model/. Train locally first;"
  echo "         /predict returns 503 until a model exists."
  exit 0
fi

FOLDER="${KEY%/*}"
echo "Downloading s3://$BUCKET/$FOLDER to $DEST"
mkdir -p "$DEST"
aws s3 sync "s3://$BUCKET/$FOLDER" "$DEST" --only-show-errors
echo "Model downloaded."
