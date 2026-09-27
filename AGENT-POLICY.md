<!-- ai-generated: 80% - Claude Code drafted the justifications, the repository owner chose the denylist -->
# Agent policy

The `reviewer` sub-agent (`.claude/agents/reviewer.md`) reads and comments. Each denied tool below is a
blast-radius decision: what could go wrong if a reviewer that misread the code were allowed to act on it.

- Bash(rm *): the reviewer reads and comments; deleting files is the author's decision, and a wrong delete under src/ or specs/ destroys work the receipts refer to.
- Bash(git push *): a push changes the public repository that the grader clones; only the author publishes, after verify 1 passed on a clean tree.
- Bash(git tag *): tags never move and each one consumes an attempt; creating or moving a lab1/v* tag is irreversible and belongs to the author alone.
- Bash(docker *): docker can stop, delete or rebuild the running service and its named volume, which would lose tickets and invalidate a local checker run in progress.
- Write: a reviewer that writes files turns a comment into an unreviewed change; findings go into the report, not into the tree.
- Edit: same blast radius as Write, only smaller per call; an edit to DECISIONS.md or sla.py silently changes the declared C1/C2/C3 behaviour.
- WebFetch: the review is against the repository and the course documents only; fetching arbitrary pages brings untrusted instructions into the agent's context.
