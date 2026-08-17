#!/bin/bash
# Install git hooks for portfolio-ai

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_DIR="$REPO_ROOT/.git/hooks"

echo "Installing pre-push hook..."
cp "$REPO_ROOT/hooks/pre-push" "$HOOK_DIR/pre-push"
chmod +x "$HOOK_DIR/pre-push"

echo "✅ Hooks installed"
