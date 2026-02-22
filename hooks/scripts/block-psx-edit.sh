#!/bin/bash
# Block direct edits to Metashape project files (.psx, .psz, .files)
# These should only be modified through the Metashape MCP server.
FILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('file_path',''))" 2>/dev/null || echo "")

if [[ "$FILE_PATH" == *.psx ]] || [[ "$FILE_PATH" == *.psz ]] || [[ "$FILE_PATH" == *.files* ]]; then
    echo "BLOCKED: Direct edits to Metashape project files (.psx/.psz/.files) are not allowed. Use the Metashape MCP server instead."
    exit 1
fi
exit 0
