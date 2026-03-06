1. Create `CLAUDE.md` (under 100 lines). `CLAUDE.md` should contain only project rules and pointers to files, not full instructions.

2. Add a `.claudeignore` file blocking large or irrelevant directories:

```

node_modules/

build/

dist/

.git/

```

3. In `.claude/settings.json`:

* Use **Opus** for complex architectural decisions

* Use **Sonnet** for most coding tasks

* Use **Haiku** for subagents (repo scanning, bug search, quick analysis)

4. Session workflow: when done with a task or switching topics, run `/clear`.

5. Session workflow: if touching **3+ files**, use **Plan Mode** (`Shift+Tab`) before implementing.

6. Use **MCP servers** only when external data or tools are needed (not for normal coding). Examples:

* Git / GitHub (repo browsing, PRs, issues)

* Filesystem or local search

* Documentation search

* Database or API access (if the app uses one)

7. Use **RLM (`rlmgw`)** for persistent memory across sessions. Stops using the LLM context window as storage.

8. Use **Hooks** to automate repeated actions, for example:

* run tests after edits

* run lint / format

* prevent edits in protected directories

* auto-run build or validation steps

9. Use `/permissions` and `/sandbox` to reduce approval fatigue while keeping risky commands restricted.

10. Create a repo-local **working memory file**, such as:

* `STILL_NEED.md`

* `working-notes.md`

* `docs/ai-notes.md`

Store short summaries of:

* decisions

* files changed

* remaining tasks

* testing instructions

11. Use **subagents** for repo exploration instead of loading large files into the main session (search, summarize, report findings).

12. Prefer **search → read small sections → summarize** instead of pasting entire files into context.

13. Use `/compact` periodically during long sessions to summarize progress and reduce token usage while preserving key decisions.