#!/bin/sh
set -e

echo "🔥 Starting container..."

# Load environment variables from /app/.env in a safe way
if [ -f "/app/.env" ]; then
  # Read file line-by-line, skip comments and empty lines, export KEY=VAL only when valid
  while IFS= read -r line || [ -n "$line" ]; do
    # Trim leading/trailing whitespace (portable)
    trimmed="$(printf '%s' "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    # Skip empty or commented lines
    case "$trimmed" in
      ''|\#*) continue ;;
    esac
    # Only export lines that contain '='
    case "$trimmed" in
      *=*)
        # Export the assignment as-is (handles values with spaces if they are quoted)
        export "$trimmed"
        ;;
      *)
        echo "⚠️  Skipping invalid .env line: $trimmed" >&2
        ;;
    esac
  done < /app/.env
fi

echo "📦 Environment loaded."
echo "🚀 Running pipeline..."

exec "$@"
