# Files Worth Submitting to GitHub

This folder contains the files that are most suitable to keep for a public-facing fork or a cleaned project repository.

## Recommended to keep

### 1. `run_vln_unseen_eval_v2.py`
A practical episode-by-episode VLN unseen evaluation runner.

Why it is worth keeping:
- it is the main engineering contribution of this round of work;
- it turns the original batch evaluation into a resumable per-episode pipeline;
- it archives per-episode outputs and computes metrics automatically.

### 2. `README_EXPERIMENT_REPORT.md`
An English experiment report suitable for GitHub.

Why it is worth keeping:
- it explains the full evaluation pipeline;
- it documents setup, challenges, solutions, and outputs;
- it is suitable as project-facing documentation.

### 3. `PROJECT_SUMMARY_20260405.md`
A detailed Chinese internal/project summary.

Why it is worth keeping:
- it preserves the original project timeline and engineering context;
- it is useful as an internal record or supplementary note.

---

## Usually worth considering later

Depending on how clean you want the public repository to be, you may later also add:

- a cleaned root `README.md`;
- a `.gitignore` file;
- small utility scripts for metrics aggregation;
- lightweight examples showing how to run the new pipeline.

---

## Not recommended to submit directly

The following are usually **not** good candidates for GitHub submission:

- large result directories;
- videos such as `episode.mp4`;
- runtime logs;
- `shared_folder/` runtime exchange files;
- dataset files;
- checkpoint/model weights;
- machine-specific absolute paths;
- temporary backups and caches.

Examples from the current workspace that should usually stay out of GitHub:

- `shared_folder/`
- `shared_folder_backup_*`
- `without_screenshot/`
- result directories under `/data1/...`
- large archives such as `training_data.zip` unless intentionally included

---

## Suggested next cleanup

Before pushing to GitHub, it is recommended to:

1. replace machine-specific absolute paths with placeholders;
2. add `.gitignore` to exclude results, videos, logs, and caches;
3. rename `README_EXPERIMENT_REPORT.md` to `README.md` if you want it to become the repo homepage;
4. keep the Chinese summary as an additional document instead of the main landing page.

