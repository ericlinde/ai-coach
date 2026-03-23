# PR #4 Review Comments Assessment

---

## 1. `sync.py:34` — `_run_git()` does not handle `FileNotFoundError`/`OSError`

> `_run_git()` only handles `subprocess.CalledProcessError`. If `git` is not installed or `cwd` doesn't exist, `subprocess.run()` will raise `FileNotFoundError` (or `OSError`) and crash the app instead of returning `False` after logging. Consider catching these exceptions and treating them as non-retriable failures with a clear log message.

- [ ] Resolved
- Agree with problem statement: Y
- Agree with solution: Y

---

## 2. `sync.py:57` — `progress_repo` URL never used to configure the git remote

> `progress_repo` is only used as an enable/disable flag; the configured repo URL is never used to set up or validate the git remote, clone, etc.

- [ ] Resolved
- Agree with problem statement: N
- Agree with solution: N
- Comment: This is intentional. The URL is consumed by Ansible at deploy time to clone the repo and configure the remote on the persistent volume. The runtime code only checks whether `progress_repo` is set (i.e. the feature is enabled for this instance). Using the URL at runtime to set up remotes would duplicate Ansible's job and break the architecture. The code should instead have a comment explaining this, and the field name is accurate — it IS the repo URL, just used at a different layer.

---

## 3. `sync.py:70` — `skills_repo` URL never used to configure the git remote

> `skills_repo` is only used for truthiness; the repo URL is never used to configure/validate the git remote.

- [ ] Resolved
- Agree with problem statement: N
- Agree with solution: N
- Comment: Same reasoning as #2. Ansible configures the remote; the runtime only checks presence. A clarifying comment in the code is warranted, but no behaviour change needed.

---

## 4. `agent.py:126` — `_refine_skills()` catches broad `Exception`

> `_refine_skills()` catches a broad `Exception` and silently continues; this can hide real errors. Catch the specific expected exception(s) (e.g. `SkillNotFoundError`) and log unexpected exceptions so failures are diagnosable.

- [ ] Resolved
- Agree with problem statement: Y
- Agree with solution: Y

---

## 5. `scheduler.py:35` — `parse_interval()` raises `ValueError` on malformed input like `"xh"` or `"m"`

> `parse_interval()` uses `int(s[:-1])` for the d/h/m formats; non-numeric values like "xh" or an empty prefix like "m" will raise `ValueError` instead of `InvalidCadenceError`.

- [ ] Resolved
- Agree with problem statement: Y
- Agree with solution: Y

---

## 6. `sync.py:56` — `sync_progress()` does not check if `progress.md` exists before `git add`

> If the progress file hasn't been created yet, `git add progress.md` will fail with a pathspec error. Consider checking for the file before adding, or skip commit/push if nothing to sync.

- [ ] Resolved
- Agree with problem statement: Y
- Agree with solution: Y

---

## 7. `sync.py:62` — `sync_progress()` ignores `_run_git()` return values

> Return values from `_run_git()` are ignored, so `sync_progress()` will continue to commit/push even after a failed `git add`/`commit`.

- [ ] Resolved
- Agree with problem statement: Y
- Agree with solution: Y

---

## 8. `sync.py:80` — `sync_skills()` ignores `_run_git()` return values

> `sync_skills()` also ignores `_run_git()` return values; if add/commit/push/pull fails, the method continues silently.

- [ ] Resolved
- Agree with problem statement: Y
- Agree with solution: Y

---

## 9. `cli.py:9` — CLI prints pending check-ins but never clears them

> The CLI prints pending check-ins but never clears them, so the same queued check-ins will be printed again on every subsequent CLI run.

- [ ] Resolved
- Agree with problem statement: Y
- Agree with solution: Y

---

## 10. `agent.py:74` — `reply()` accesses `SkillsCache._dir` (private attribute)

> `reply()` reaches into `SkillsCache`'s private `_dir` and re-reads every skill file to infer `selected_topics` from `selected_skills` content. This is fragile and couples `CoachAgent` to `SkillsCache` internals. Prefer having `SkillsCache.select()` return topic identifiers alongside content (e.g. a `{topic: content}` mapping).

- [ ] Resolved
- Agree with problem statement: Y
- Agree with solution: Y

---

## 11. `slack_bot.py:13` — `SlackBot` takes a `MemoryStore` dependency, contradicting PLAN.md

> This introduces a `MemoryStore` dependency into `SlackBot`. PLAN.md states the Slack bot "depends on CoachAgent only".

- [ ] Resolved
- Agree with problem statement: Y
- Agree with solution: partial
- Comment: The problem is real. The suggested fix ("move pending-checkin flushing outside of SlackBot") is the right direction, but needs a concrete form. The cleanest approach is: `main.py` drains the queue before starting the bot and passes the messages directly, keeping `SlackBot` free of `MemoryStore`. Alternatively, `CoachAgent` could expose a `get_and_clear_pending_checkins()` method so `SlackBot` only ever talks to the agent. Either way, `MemoryStore` should not appear in `SlackBot`'s constructor.

---

## 12. `config.py:58` — `update_cadence()` does not handle `FileNotFoundError` or `JSONDecodeError`

> `update_cadence()` reads/parses the config file without handling `FileNotFoundError` or `JSONDecodeError`, giving callers inconsistent low-level exceptions instead of `ConfigError`.

- [ ] Resolved
- Agree with problem statement: Y
- Agree with solution: Y

---

## 13. `scheduler.py:85` — `update_cadence()` will `AttributeError` if called before `start()`

> `update_cadence()` assumes `self._job` is set; if called before `start()`, it will raise `AttributeError` at `self._job.reschedule(...)`. Add an explicit guard.

- [ ] Resolved
- Agree with problem statement: Y
- Agree with solution: Y
