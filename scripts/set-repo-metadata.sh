#!/usr/bin/env bash
# Set the GitHub repository description, homepage, and topics.
#
# These live in GitHub's repository settings, not in the repo tree, so they
# cannot be committed. Run this once (requires the `gh` CLI, authenticated with
# a token that has repo admin scope):
#
#   ./scripts/set-repo-metadata.sh
#
# Afterwards, enable GitHub Pages under Settings → Pages with source
# "GitHub Actions" so .github/workflows/docs.yml can publish the docs site.

set -euo pipefail

REPO="${REPO:-eputnam77/DocReview360}"

DESCRIPTION="Open-source document review, approval, version control, and audit workflow platform for technical and regulated documents."
HOMEPAGE="https://eputnam77.github.io/DocReview360/"

# GitHub allows up to 20 topics; they drive repository discovery and topic pages.
TOPICS=(
  document-review
  document-management
  document-approval
  approval-workflow
  document-workflow
  document-control
  review-workflow
  audit-trail
  version-control
  technical-writing
  compliance
  self-hosted
  open-source
  fastapi
  nextjs
)

echo "Updating description and homepage for ${REPO}..."
gh repo edit "${REPO}" \
  --description "${DESCRIPTION}" \
  --homepage "${HOMEPAGE}"

echo "Setting topics..."
gh repo edit "${REPO}" $(printf -- '--add-topic %s ' "${TOPICS[@]}")

echo "Done. Current settings:"
gh repo view "${REPO}" --json description,homepageUrl,repositoryTopics
