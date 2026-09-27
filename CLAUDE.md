<!-- ai-generated: 90% - Claude Code drafted, reviewed by the repository owner -->
# svcdesk - notes for coding agents

- The service lives in `src/svcdesk/` (FastAPI, Python 3.13): `main.py` is the HTTP layer and the state machine,
  `sla.py` the priority matrix and both SLA clocks, `store.py` the SQLite persistence.
- The contract is the course's API.md; the three decisions (C1 = wallclock, C2 = immutable, C3 = vip) are recorded
  in `DECISIONS.md`. Code must keep exhibiting exactly those values: the checker compares them.
- Own tests: `docker compose --profile tests run --rm --build tests`. Full check: `.\itsmlab.ps1 verify 1`.
- Never add bind mounts to `docker-compose.yml`, never install anything at container start, and never move a
  `lab1/v*` tag once it has been pushed.
- Every file under `src/` and `specs/` with a code or Markdown extension carries an `ai-generated:` header.
- Sub-agents and what they may never do are in `.claude/agents/`; the reasons are in `AGENT-POLICY.md`.
