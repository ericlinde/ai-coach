# PR #4 Review Comments Assessment

---

## 1. `sync.py:34` — `_run_git()` does not handle `FileNotFoundError`/`OSError`

> `_run_git()` only handles `subprocess.CalledProcessError`. If `git` is not installed or `cwd` doesn't exist, `subprocess.run()` will raise `FileNotFoundError` (or `OSError`) and crash the app instead of returning `False` after logging. Consider catching these exceptions and treating them as non-retriable failures with a clear log message.

- [x] Resolved
- Agree with problem statement: Y
- Agree with solution: Y

---

## 2. `sync.py:57` — `progress_repo` URL never used to configure the git remote

> `progress_repo` is only used as an enable/disable flag; the configured repo URL is never used to set up or validate the git remote, clone, etc.

- [x] Resolved
- Agree with problem statement: Y
- Agree with solution: N
- Comment: The sync methods don't need to configure the remote themselves — that is Ansible's job. But the URL should appear in error messages when a sync fails, so the operator knows which repo the push/pull was targeting. Fix: when `_run_git()` logs a failure, also run `git remote get-url origin` and include the result in the error message. No URL validation or remote reconfiguration needed.

---

## 3. `sync.py:70` — `skills_repo` URL never used to configure the git remote

> `skills_repo` is only used for truthiness; the repo URL is never used to configure/validate the git remote.

- [x] Resolved
- Agree with problem statement: Y
- Agree with solution: N
- Comment: Same reasoning and same fix as #2. On failure, log the actual remote URL from `git remote get-url origin` so the operator can diagnose which repo was involved.

---

## 4. `agent.py:126` — `_refine_skills()` catches broad `Exception`

> `_refine_skills()` catches a broad `Exception` and silently continues; this can hide real errors. Catch the specific expected exception(s) (e.g. `SkillNotFoundError`) and log unexpected exceptions so failures are diagnosable.

- [x] Resolved
- Agree with problem statement: Y
- Agree with solution: Y

---

## 5. `scheduler.py:35` — `parse_interval()` raises `ValueError` on malformed input like `"xh"` or `"m"`

> `parse_interval()` uses `int(s[:-1])` for the d/h/m formats; non-numeric values like "xh" or an empty prefix like "m" will raise `ValueError` instead of `InvalidCadenceError`.

- [x] Resolved
- Agree with problem statement: Y
- Agree with solution: Y

---

## 6. `sync.py:56` — `sync_progress()` does not check if `progress.md` exists before `git add`

> If the progress file hasn't been created yet, `git add progress.md` will fail with a pathspec error. Consider checking for the file before adding, or skip commit/push if nothing to sync.

- [x] Resolved
- Agree with problem statement: Y
- Agree with solution: Y

---

## 7. `sync.py:62` — `sync_progress()` ignores `_run_git()` return values

> Return values from `_run_git()` are ignored, so `sync_progress()` will continue to commit/push even after a failed `git add`/`commit`.

- [x] Resolved
- Agree with problem statement: Y
- Agree with solution: Y

---

## 8. `sync.py:80` — `sync_skills()` ignores `_run_git()` return values

> `sync_skills()` also ignores `_run_git()` return values; if add/commit/push/pull fails, the method continues silently.

- [x] Resolved
- Agree with problem statement: Y
- Agree with solution: Y

---

## 9. `cli.py:9` — CLI prints pending check-ins but never clears them

> The CLI prints pending check-ins but never clears them, so the same queued check-ins will be printed again on every subsequent CLI run.

- [x] Resolved
- Agree with problem statement: Y
- Agree with solution: Y

---

## 10. `agent.py:74` — `reply()` accesses `SkillsCache._dir` (private attribute)

> `reply()` reaches into `SkillsCache`'s private `_dir` and re-reads every skill file to infer `selected_topics` from `selected_skills` content. This is fragile and couples `CoachAgent` to `SkillsCache` internals. Prefer having `SkillsCache.select()` return topic identifiers alongside content (e.g. a `{topic: content}` mapping).

- [x] Resolved
- Agree with problem statement: Y
- Agree with solution: Y

---

## 11. `slack_bot.py:13` — `SlackBot` takes a `MemoryStore` dependency, contradicting PLAN.md

> This introduces a `MemoryStore` dependency into `SlackBot`. PLAN.md states the Slack bot "depends on CoachAgent only".

- [x] Resolved
- Agree with problem statement: Y
- Agree with solution: Y
- Comment: Fix: `main.py` drains the queue from `MemoryStore` before starting the bot and passes the messages as a plain `list[str]`. `SlackBot.flush_pending_checkins` takes that list directly — no `MemoryStore` in the constructor or anywhere in `SlackBot`. This keeps both `CoachAgent` and `SlackBot` free of queue-management logic; the wiring layer handles startup sequencing.

---

## 12. `config.py:58` — `update_cadence()` does not handle `FileNotFoundError` or `JSONDecodeError`

> `update_cadence()` reads/parses the config file without handling `FileNotFoundError` or `JSONDecodeError`, giving callers inconsistent low-level exceptions instead of `ConfigError`.

- [x] Resolved
- Agree with problem statement: Y
- Agree with solution: Y

---

## 13. `scheduler.py:85` — `update_cadence()` will `AttributeError` if called before `start()`

> `update_cadence()` assumes `self._job` is set; if called before `start()`, it will raise `AttributeError` at `self._job.reschedule(...)`. Add an explicit guard.

- [x] Resolved
- Agree with problem statement: Y
- Agree with solution: Y
