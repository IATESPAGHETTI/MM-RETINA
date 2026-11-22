# Agent mailbox (Claude <-> Codex)

File-based; works only while each agent is active and checks it. One writer per file.

- `mailbox/claude_to_codex.md` — written ONLY by Claude (lives in Claude's worktree:
  `C:\Users\ASUS\Downloads\prj4\.claude\worktrees\github-push-status-fdb470\mailbox\`). Append-only, newest at bottom.
- `codex_to_claude.md` — written ONLY by Codex, in Codex's own worktree under `mailbox/`.
  Codex: tell the user that path so Claude can read it (or paste it into `AGENT_PLAN.md` -> "Requests between agents").

Message format (append, never edit old ones):

    ## YYYY-MM-DD HH:MM  <from> -> <to>  [READY | REQUEST | BLOCKED | INFO]
    <what, with exact artifact paths and, for results, the checkpoint/run ID they belong to>

Rules: results are only announced as READY when the files exist and the run finished; artifact paths are absolute;
anything tied to a model states which checkpoint/run produced it; synthetic or placeholder data is labeled as such.
