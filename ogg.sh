#!/usr/bin/env bash

DIR="${1:-}"

if [[ -z "$DIR" ]]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

find "$DIR" -type f -iname "*.wav" -print0 |
xargs -0 -P"$(nproc)" -n1 bash -c '
    input="$1"
    output="${input%.wav}.ogg"

    echo "Converting: $input"

    rm -f -- "$output"

    if oggenc -q 6 -o "$output" "$input" >/dev/null 2>&1; then
        rm -- "$input"
        exit 0
    fi

    rm -f -- "$output"

    if ffmpeg -nostdin -loglevel error -y \
        -i "$input" -c:a libvorbis -q:a 6 "$output"; then
        rm -- "$input"
        exit 0
    fi

    echo "ERROR: Failed to convert $input" >&2
    rm -f -- "$output"
    exit 1
' _
