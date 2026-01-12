DIR="$1"

if [[ -z "$DIR" ]]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

find "$DIR" -type f -iname "*.wav" -print0 | \
xargs -0 -P"$(nproc)" -n1 bash -c '
    input_file="$1"
    output_file="${input_file%.*}.ogg"

    [[ -e "$output_file" ]] && rm -f -- "$output_file"

    echo "Converting: $input_file"
    if oggenc -q 6 -o "$output_file" "$input_file"; then
        rm -- "$input_file"
    else
        echo "Error converting $input_file" >&2
        rm -f -- "$output_file"
        exit 1
    fi
' _

