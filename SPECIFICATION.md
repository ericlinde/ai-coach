# ai-coach — Specification

## 1. Overview

**ai-coach** is a personal AI coach that guides a single developer on their journey toward becoming a skilled AI-native developer. Its sole purpose is mentoring — it does not build, deploy, or automate anything on the user's behalf.

The coach is always accessible. The user can ask it questions at any time, and it will proactively reach out with prompts and check-ins at a cadence the user controls.

---

## 2. Users

Each deployment of ai-coach serves exactly one developer: its owner. It is not a multi-tenant system and makes no provision for teams or shared access. The software supports multiple independent deployments — one per person — but each deployment is strictly single-user.

---

## 3. Interaction Model

The user may interact with the coach through two interfaces:

- **Slack** — the always-on channel; the coach receives messages and sends replies via a Slack DM. Proactive check-ins are delivered here.
- **CLI** — a terminal-based interface for use when the user is already at their machine. On startup, any pending check-in prompts are surfaced before the interactive session begins.

Regardless of interface:

- The user may ask the coach questions at any time; the coach shall respond with guidance relevant to the user's current level and progress.
- The coach shall proactively send unprompted check-ins and prompts at a frequency the user configures.
- The user shall be able to change the check-in frequency at any time.
- The coach shall adapt its guidance based on accumulated knowledge of the user's progress and demonstrated understanding.
- All interactions, regardless of interface, contribute to the same shared memory and progress record.

---

## 4. Curriculum

The coach guides the user across four subject areas:

### 4.1 Building Safe Software Factories

What it means to construct an AI-driven development workflow safely — scoping agent authority, preserving human oversight, and avoiding uncontrolled autonomous action.

### 4.2 Writing Effective, Reusable Claude Skills

How to author Claude skill definitions that are composable, well-scoped, and useful across projects.

### 4.3 Automated Code Review

How to use AI to review code for functional correctness, conventional security vulnerabilities, and threats specific to AI-generated code (prompt injection, hallucinated constructs, unverified dependencies).

### 4.4 Multi-Repository Coordination

How to reason about and manage AI-assisted development workflows that span more than one repository.

---

## 5. Memory and Progress Tracking

- The system shall remember what topics have been discussed and the depth to which the user has engaged with them.
- The system shall maintain a running progress record that is accessible to the user on request.
- The system shall use prior context to personalise future responses — surfacing relevant past discussion, adjusting depth, and avoiding repetition.
- The system shall periodically sync the progress record to a GitHub repository configured by the user. The sync target is separate from the `ai-coach` repository and is set per user, so independent coach instances can be run for different people without interfering with one another.

---

## 6. Coaching Skills

The coach's approach to each topic is guided by a set of coaching skill definitions — structured notes that capture effective explanations, useful analogies, and known pitfalls for each subject area.

- Coaching skills shall be built and refined interactively: when the user signals that an explanation worked well or poorly, the coach shall update the relevant skill accordingly.
- Coaching skills shall be stored in a dedicated GitHub repository separate from both `ai-coach` and the user's progress repository. This repository is owned by the coach's operator.
- The system shall sync coaching skills from that repository on a daily schedule, so improvements made during one user's sessions are available to all coach instances the next day.
- Coach instances for other users shall pull from the same skills repository but shall not write back to it — only the owner's coach can update skills.

---

## 7. Proactive Prompting

- The system shall send unprompted check-ins at a frequency the user sets.
- The user shall be able to change the check-in frequency at any time by sending a message to the coach.
