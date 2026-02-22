#!/bin/bash
# Block direct edits to API reference files (imported from Agisoft, not user-generated).
FILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('file_path',''))" 2>/dev/null || echo "")

if [[ "$FILE_PATH" == *api_reference.txt ]] || [[ "$FILE_PATH" == *.pdf ]]; then
    echo "BLOCKED: Reference files (api_reference.txt, PDFs) are imported from Agisoft and should not be edited directly."
    exit 1
fi
exit 0
