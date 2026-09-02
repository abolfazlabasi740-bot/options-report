#!/usr/bin/env bash
set -Eeuo pipefail

# Persist only the downloaded Optionschool workbooks.  The next scheduled run
# uses these point-in-time files for the seven-day transition/learning engine.
# Reports, logs and snapshots remain immutable run artifacts in Actions.

project_root="${PROJECT_ROOT:-smart_money_project}"
branch="${GITHUB_REF_NAME:-main}"

if [[ ! -d .git ]]; then
  echo "::warning::No Git repository is available; seven-day history was not persisted."
  exit 0
fi

shopt -s nullglob
files=("${project_root}/data/raw"/optionschool24_all_*.xlsx)
if (( ${#files[@]} == 0 )); then
  echo "::warning::No Optionschool workbook was found for history persistence."
  exit 0
fi

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

# The checkout action normally leaves a detached HEAD.  Push the generated
# commit explicitly to the triggering/default branch.
git add -f "${files[@]}"
if git diff --cached --quiet; then
  echo "No new workbook to persist."
  exit 0
fi

git commit -m "data: persist Optionschool point-in-time workbook [skip ci]"
for attempt in 1 2 3; do
  if git push origin "HEAD:${branch}"; then
    echo "Persisted Optionschool history to ${branch}."
    exit 0
  fi
  if (( attempt < 3 )); then
    echo "Push attempt ${attempt} failed; refreshing remote branch before retry."
    git fetch origin "${branch}" || true
    git rebase "origin/${branch}" || {
      git rebase --abort || true
      echo "::warning::Remote branch changed; history commit will be retried on the next run."
      exit 0
    }
    sleep $((attempt * 2))
  fi
done

echo "::warning::Could not persist workbook history after three attempts."
exit 0
