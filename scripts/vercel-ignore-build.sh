#!/bin/bash

# This script tells Vercel to IGNORE builds on master/main branches
# because GitHub Actions will handle production deployments

echo "Checking if build should be ignored..."

# Get the current branch name
BRANCH="${VERCEL_GIT_COMMIT_REF}"

echo "Branch: $BRANCH"

# Ignore builds on master and main branches
if [[ "$BRANCH" == "master" ]] || [[ "$BRANCH" == "main" ]]; then
    echo "🚫 Ignoring build on $BRANCH - GitHub Actions will handle deployment"
    exit 0  # Exit 0 = ignore build
fi

# Allow builds on other branches (PRs, preview deployments)
echo "✅ Allowing build on $BRANCH (preview deployment)"
exit 1  # Exit 1 = proceed with build
