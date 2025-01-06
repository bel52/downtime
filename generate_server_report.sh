#!/bin/bash

# Define the directory to scan and the output file
TARGET_DIR="/home/brett/server-management"
OUTPUT_FILE="server_management_report.txt"

# Start the report
{
    echo "Server Management Directory Report"
    echo "Generated on: $(date)"
    echo "==================================="
    echo ""
} > "$OUTPUT_FILE"

# Verify the directory exists
if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Directory $TARGET_DIR does not exist." >> "$OUTPUT_FILE"
    echo "Report generation failed." >> "$OUTPUT_FILE"
    exit 1
fi

# List directory structure and permissions, excluding venv, __pycache__ directories, .db files, and the output file
{
    echo "Directory Structure and Permissions:"
    echo "-----------------------------------"
    find "$TARGET_DIR" \
        -path "$TARGET_DIR/venv" -prune -o \
        -path "*/__pycache__" -prune -o \
        -name "$(basename "$OUTPUT_FILE")" -prune -o \
        -name "*.db" -prune -o \
        -exec ls -ld {} \;
    echo ""
} >> "$OUTPUT_FILE"

# Include file contents for all files, excluding venv, __pycache__ directories, .db files, and the output file
{
    echo "File Contents:"
    echo "-----------------------------------"
    find "$TARGET_DIR" \
        -path "$TARGET_DIR/venv" -prune -o \
        -path "*/__pycache__" -prune -o \
        -name "$(basename "$OUTPUT_FILE")" -prune -o \
        -name "*.db" -prune -o \
        -type f -print | while IFS= read -r file; do
        echo "-----------------------------------"
        echo "File: $file"
        echo "-----------------------------------"
        if [ -r "$file" ]; then
            cat "$file"
        else
            echo "Error: File not readable."
        fi
        echo ""
    done
} >> "$OUTPUT_FILE"

# Notify the user
echo "Report generated: $OUTPUT_FILE"
