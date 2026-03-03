#!/bin/bash

# Get the absolute path of $1
ABS_PATH1=$(realpath "$1")
DIR_PATH1=$(dirname "$ABS_PATH1")

# Extract the directory path from $2
DIR_PATH=$(dirname "$2")
BASE_NAME=$(basename "$DIR_PATH")

# Check if the directory name ends with ".aedb"
if [[ "$BASE_NAME" != *.aedb ]]; then
  NEW_DIR_PATH="${DIR_PATH}.aedb"
  mv "$DIR_PATH" "$NEW_DIR_PATH"
  # Update $2 to point to the new path
  UPDATED_PATH="${NEW_DIR_PATH}/$(basename "$2")"
else
  UPDATED_PATH="$2"
fi

# Run the edbdiff command with the updated path
echo "Running edbdiff on $DIR_PATH1 and $NEW_DIR_PATH"
edbdiff $DIR_PATH1 $NEW_DIR_PATH