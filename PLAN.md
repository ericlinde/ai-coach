# ai-coach — Implementation Plan

## Project structure

```
ai-coach/
  src/
    coach/
      config.py        # load/validate config.json
      memory.py        # MemoryStore: read/write agent_state, progress, sessions
      skills.py        # SkillsCache: load and select relevant skill files
      agent.py         # CoachAgent: prompt assembly, Claude API call, memory update
      sync.py          # RepoSync: progress push, skills pull/push
    interfaces/
      slack_bot.py     # Slack Bolt app: event listener, send messages
      cli.py           # CLI: readline loop
    scheduler.py       # APScheduler: check-in trigger
    main.py            # entry point: wire everything together and start
  tests/
    test_config.py
    test_memory.py
    test_skills.py
    test_agent.py
    test_sync.py
    test_slack.py
    test_scheduler.py
  ansible/
    site.yml                   # main playbook: runs provision → configure → deploy roles
    ansible.cfg                # sets inventory default and SSH options; manages Fly host keys via known_hosts (host key checking enabled)
    roles/
      provision/               # create Fly app and persistent volume if absent
      configure/               # write config.json to volume, set Fly secrets
      deploy/                  # flyctl deploy --app {{ fly_app }}
    inventory/
      owner.yml                # instance vars: fly_app, progress_repo, write_back, etc.
      # colleague-alice.yml    # added when setting up a new instance
  scripts/
    test.sh                    # install deps, run pytest (used by CI and locally)
  .github/
    workflows/
      ci.yml                   # on PR: calls scripts/test.sh
      _deploy.yml              # reusable workflow: runs ansible-playbook with given inventory
      deploy-owner.yml         # on push to main: calls _deploy.yml, inventory=owner.yml
  skills/                      # local skills cache (synced from skills repo, gitignored)
  memory/                      # per-user memory (gitignored)
  Dockerfile
  fly.toml
  pyproject.toml
  README.md
```

**Dependency direction:** `interfaces` and `scheduler` depend on `agent`; `agent` depends on `memory` and `skills`; nothing depends on `interfaces`. This keeps the core testable without any Slack or Claude API involvement.

---

## Phase 0 — Project setup

Goal: runnable skeleton with test infrastructure in place before any feature code is written.

- [ ] Initialise `pyproject.toml` with dependencies: `anthropic`, `slack-bolt`, `apscheduler`, `pytest`, `pytest-mock`
- [ ] Create the directory structure above with empty `__init__.py` files
- [ ] Add `.gitignore` entries for `memory/` and `skills/`
- [ ] Write a minimal `config.py` that loads and validates `memory/config.json` (check-in frequency, progress repo, skills repo URL, write-back flag); raise clearly if required fields are missing
- [ ] Write `tests/test_config.py`: valid config loads correctly; missing required fields raise; unknown fields are ignored
- [ ] Confirm `pytest` runs and all tests pass (trivially, at this point)

---

## Phase 1 — Memory Store

Goal: reliable, tested read/write layer for all memory files. Everything else builds on this.

`memory.py` exposes a `MemoryStore` class constructed with a base path. It is the only code that touches the filesystem for memory.

- [ ] Implement `MemoryStore.load_agent_state() -> str` — reads `agent_state.md`; returns empty string if file does not exist
- [ ] Implement `MemoryStore.save_agent_state(content: str)` — writes `agent_state.md`
- [ ] Implement `MemoryStore.load_progress() -> str` — reads `progress.md`
- [ ] Implement `MemoryStore.save_progress(content: str)` — writes `progress.md`
- [ ] Implement `MemoryStore.append_session_turn(date: str, role: str, content: str)` — appends a turn to `sessions/YYYY-MM-DD.json`, creating the file if needed
- [ ] Implement `MemoryStore.load_pending_checkins() -> list[str]` and `clear_pending_checkins()` — simple queue stored in `memory/pending_checkins.json`; never written to `config.json`, which is declarative and Ansible-managed

Tests (`test_memory.py`) — use `tmp_path` fixture throughout, no real filesystem side effects:
- [ ] `load_agent_state` returns empty string when file absent
- [ ] Round-trip: save then load returns the same content
- [ ] `append_session_turn` creates the file on first call; subsequent calls append correctly
- [ ] Pending check-in queue: enqueue, load, clear

---

## Phase 2 — Skills Cache

Goal: the agent can ask for relevant skills and get back only what fits the current conversation.

`skills.py` exposes a `SkillsCache` class constructed with a skills directory path.

- [ ] Implement `SkillsCache.all_topics() -> list[str]` — returns the stem of each `.md` file in the skills directory
- [ ] Implement `SkillsCache.load(topic: str) -> str` — reads `skills/{topic}.md`; raises if not found
- [ ] Implement `SkillsCache.select(keywords: list[str]) -> list[str]` — returns the content of skill files whose filename or first-line heading matches any keyword; returns empty list if skills directory is empty
- [ ] Implement `SkillsCache.update(topic: str, content: str)` — writes `skills/{topic}.md` (creates if new)

Tests (`test_skills.py`) — use `tmp_path`:
- [ ] `all_topics` returns correct stems; empty list when directory is empty
- [ ] `load` returns content; raises on unknown topic
- [ ] `select` matches on filename; returns empty list when no match; returns empty list when directory is empty
- [ ] `update` creates new file; overwrites existing file

---

## Phase 3 — Coach Agent

Goal: the core coaching loop, fully testable without real Claude or Slack calls.

`agent.py` exposes a `CoachAgent` class that takes a `MemoryStore`, a `SkillsCache`, and a callable `llm` (the Claude API call). Injecting `llm` as a dependency keeps tests fast and free of network calls.

- [ ] Implement `CoachAgent.reply(user_message: str) -> str`:
  - loads `agent_state.md` and selects relevant skills based on the user message
  - assembles the system prompt (agent state + selected skills) and the conversation turn
  - calls `llm(system, messages) -> str`
  - appends the turn to the session log
  - updates `agent_state.md` and `progress.md` via a second `llm` call (or inline if agent state update is rule-based)
  - returns the response
- [ ] Implement `CoachAgent.checkin() -> str` — generates a proactive prompt (no user message); same update path as `reply`
- [ ] Implement skill refinement: if the response or a follow-up turn contains a signal that an explanation worked/failed, call `SkillsCache.update` with an improved version of the relevant skill
- [ ] Wire the real Claude API call in `main.py` (one function, injected into `CoachAgent`)

Tests (`test_agent.py`) — inject a mock `llm`:
- [ ] `reply` passes agent state and selected skills in the system prompt
- [ ] `reply` appends both turns (user + assistant) to the session log
- [ ] `reply` calls `save_agent_state` after each turn
- [ ] `checkin` produces a response without a user message
- [ ] Skill refinement updates the correct skill file when a signal is detected
- [ ] `reply` works correctly when skills directory is empty (no skills loaded yet)

---

## Phase 4 — Slack Bot

Goal: receive Slack messages and send replies using the Coach Agent.

`slack_bot.py` constructs a Slack Bolt `App`, registers handlers, and exposes a `start()` function. It depends on `CoachAgent` only — it knows nothing about memory or skills directly.

- [ ] Register a `message` handler: extract text, call `agent.reply()`, post response back to the same channel
- [ ] Register a startup hook that posts any pending check-ins on bot start
- [ ] Expose `send_message(text: str)` for use by the scheduler

Tests (`test_slack.py`) — use Slack Bolt's test client or mock the `say` callable:
- [ ] Incoming message triggers `agent.reply` with correct text
- [ ] Response is passed to `say`
- [ ] Pending check-ins are sent on startup

---

## Phase 5 — CLI

Goal: a simple terminal loop that uses the same Coach Agent.

`cli.py` exposes a `run(agent: CoachAgent)` function. It has no logic beyond the loop itself.

- [ ] On start, fetch and print pending check-ins from the memory store's pending queue (do not call `agent.checkin()` here — that generates a new prompt; the queue only contains check-ins already created by the scheduler)
- [ ] Loop: print prompt, read line, call `agent.reply()`, print response
- [ ] Exit cleanly on EOF (`Ctrl-D`) or the string `exit`

Tests (`test_cli.py`) — use `monkeypatch` to replace `input`:
- [ ] Pending check-ins are printed before the first prompt
- [ ] Each line of input produces one call to `agent.reply`
- [ ] EOF exits the loop without error

---

## Phase 6 — Scheduler

Goal: proactive check-ins sent to Slack at the configured cadence.

`scheduler.py` exposes a `start(agent: CoachAgent, send_message, config)` function that configures APScheduler and starts it in-process.

- [ ] Schedule a job at the configured interval that calls `agent.checkin()` and passes the result to `send_message`
- [ ] Read the interval from `config` on start; restart the job if the user changes the cadence at runtime

Tests (`test_scheduler.py`) — mock APScheduler or inject a fake clock:
- [ ] Job is scheduled with the correct interval from config
- [ ] Job calls `agent.checkin()` and forwards result to `send_message`

---

## Phase 7 — Repo Sync

Goal: daily push of `progress.md` and pull/push of skill files.

`sync.py` exposes a `RepoSync` class constructed with a `MemoryStore`, a `SkillsCache`, and a config. Both methods use `subprocess` to call `git` and encapsulate all git interaction — including error handling and basic retry/backoff for transient push/pull failures.

- [ ] Implement `RepoSync.sync_progress()`: commits and pushes `memory/progress.md` to the configured remote repo
- [ ] Implement `RepoSync.sync_skills()`: if write-back enabled, stages and pushes modified skill files first; then pulls from the skills remote
- [ ] Both methods are no-ops (log and return) if the relevant repo URL is not configured
- [ ] Both methods log a clear error and retry with exponential backoff on transient git failures (network/credential errors); give up and log after a fixed number of attempts rather than blocking indefinitely

Tests (`test_sync.py`) — construct `RepoSync` with fakes; mock `subprocess.run`:
- [ ] `sync_progress` runs the correct git commands with the correct remote
- [ ] `sync_skills` pushes before pulling when write-back is enabled
- [ ] `sync_skills` only pulls when write-back is disabled
- [ ] Both methods skip gracefully when repo URL is absent
- [ ] Transient failure triggers retry; permanent failure logs and exits cleanly

---

## Phase 8 — Wiring and Ansible deployment

Goal: the application starts correctly and any instance can be provisioned and deployed with a single `ansible-playbook` command, locally or from CI.

**Application wiring:**
- [ ] `main.py`: load config → construct `MemoryStore`, `SkillsCache`, `CoachAgent` → start scheduler → start Slack bot
- [ ] CLI remains a separate entry point (`python -m coach.interfaces.cli`) that constructs the same graph and calls `cli.run(agent)`
- [ ] Write `Dockerfile`: Python 3.12-slim base, install dependencies, copy source, set entry point to `main.py`
- [ ] Write `fly.toml`: single process, AMS region — app name left as a template variable (`{{ fly_app }}`), resolved by Ansible at deploy time
- [ ] Write `scripts/test.sh`: install dependencies, run `pytest`; exits non-zero on failure

**Ansible playbook and roles:**
- [ ] Write `ansible/site.yml`: runs three roles in order — `provision`, `configure`, `deploy`
- [ ] Write `ansible/roles/provision`: use `command: flyctl apps list` to check existence before `flyctl apps create`; create a persistent volume for `/data` (holds `memory/` and `skills/`) if absent; idempotent
- [ ] Write `ansible/roles/configure`: set Fly secrets (`SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `ANTHROPIC_API_KEY`) from Ansible vars; render `memory/config.json` from a Jinja2 template using inventory variables (`progress_repo`, `skills_repo`, `write_back`, `checkin_frequency`, `model_id`)
- [ ] Write `ansible/roles/deploy`: run `flyctl deploy --app {{ fly_app }} --remote-only`
- [ ] Write `ansible/inventory/owner.yml`: populate all instance variables for the owner's deployment
- [ ] Write `ansible/ansible.cfg`: set default inventory, configure SSH settings for Fly

**Verify locally before wiring CI:**
- [ ] Run `ansible-playbook ansible/site.yml -i ansible/inventory/owner.yml` from a developer machine; confirm app is created, configured, and running

---

## Phase 9 — CI/CD pipeline

Goal: tests run on every PR; the owner's instance deploys on every push to `main`. GitHub Actions is a thin trigger layer over Ansible and `scripts/test.sh`.

- [ ] Write `.github/workflows/ci.yml`: trigger on pull request; single step calls `scripts/test.sh`
- [ ] Write `.github/workflows/_deploy.yml` (reusable workflow): accepts `inventory` input and `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `ANTHROPIC_API_KEY`, `FLY_API_TOKEN` secrets; single step runs `ansible-playbook ansible/site.yml -i ansible/inventory/${{ inputs.inventory }}`
- [ ] Write `.github/workflows/deploy-owner.yml`: triggers on push to `main`; calls `_deploy.yml` with `inventory: owner.yml` and owner's secrets
- [ ] Add secrets to the GitHub repository: `OWNER_SLACK_BOT_TOKEN`, `OWNER_SLACK_APP_TOKEN`, `OWNER_ANTHROPIC_API_KEY`, `FLY_API_TOKEN` (manual step, documented in README)
- [ ] Verify: open a PR with a failing test → CI goes red; merge a passing PR → Ansible runs and deployment completes

**Adding a new instance (e.g. a colleague):**
- [ ] Add `ansible/inventory/colleague-alice.yml` with Alice's instance variables
- [ ] Add `.github/workflows/deploy-colleague-alice.yml` calling `_deploy.yml` with `inventory: colleague-alice.yml` and Alice's secrets
- [ ] Add Alice's secrets to the GitHub repository: `ALICE_SLACK_BOT_TOKEN`, `ALICE_SLACK_APP_TOKEN`, `ALICE_ANTHROPIC_API_KEY`

---

## Phase 10 — README setup guide

Goal: a new operator can go from zero to a running coach instance by following the README alone.

The README is written for humans. It calls out explicitly what must be done by hand and references Ansible for everything else.

**Sections to write:**

- [ ] **Prerequisites** — accounts and tools required before starting: GitHub account, Fly.io account, Slack workspace admin access, `flyctl` CLI, `ansible` CLI, Python 3.12, `git`
- [ ] **One-time: create a Slack app** — step-by-step: create app, enable Socket Mode, add bot scopes (`chat:write`, `im:history`, `im:write`), install to workspace, note the Bot Token and App Token
- [ ] **One-time: create the skills repo** — create a new empty GitHub repo; note its clone URL
- [ ] **One-time: create the progress repo** — create a new empty GitHub repo; note its clone URL
- [ ] **One-time: populate the inventory file** — copy `ansible/inventory/owner.yml.example`, fill in `fly_app`, `progress_repo`, `skills_repo`, `write_back`, `checkin_frequency`, `model_id`
- [ ] **One-time: deploy** — run `ansible-playbook ansible/site.yml -i ansible/inventory/owner.yml`; confirm the bot comes online in Slack
- [ ] **One-time: configure GitHub Actions** — add the four secrets to the repo; from this point, every push to `main` deploys automatically
- [ ] **Ongoing: how deployments work** — push to `main`; `deploy-owner.yml` triggers; Ansible provisions (no-ops if already done) and deploys
- [ ] **Running the CLI** — `ssh` to the Fly machine or run locally; invoke `python -m coach.interfaces.cli`
- [ ] **Setting up a second coach instance** — add an inventory file, add a caller workflow, add secrets; run `ansible-playbook` once to bootstrap; subsequent deploys are automatic
- [ ] **Configuration reference** — document every field in the inventory file and `memory/config.json`

---

## What is deliberately out of scope

- Multi-user support (one deployment per user)
- Web UI
- Streaming responses (standard request/response is sufficient)
- Database (plain files are the store)
- Authentication (single-user; Slack and SSH handle access control)
