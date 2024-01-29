#!/bin/bash
# This is used in tests.

# Write a message to stderr, like aplay does.
echo "message from fake aplay" >&2

# Store command-line arguments to file so we can see how aplay was called.
echo "$@" > "$(dirname "$0")"/aplay_args.txt
