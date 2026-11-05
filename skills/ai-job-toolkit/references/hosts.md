# Host capabilities and installation

The skill is portable Markdown plus standard-library Python. It uses the reasoning model already running in the host. No provider key or model subscription is bundled.

Local PDF import optionally uses `pypdf` or the host's existing PDF reader. Other import formats and the state helper need no third-party Python packages. Account export import does not connect an account; direct account reading requires an available permitted connector/browser and the user's authorization.

| Operation | Required host capability |
|---|---|
| Profile and tracking | Read/write files and run Python 3.10+ |
| Discovery and contacts | Web search/retrieval or permitted source connector |
| Documents | File creation; a document/PDF renderer for verified final outputs |
| Form filling | Connected browser/computer tool with inspect, click, type, upload, navigation |
| Submission | Browser capability, applicable host approvals, and recorded user authorization |
| Sending outreach | A connected messaging tool plus separate user authorization |

Discover the host's actual tools and read their documentation before using them. Do not invent MCP names or translate one host's browser calls into another's by guessing. Use available browser session IDs rather than reading cookie databases, exporting cookies, or reusing credentials behind the host's controls. Prefer user handoff for login/MFA challenges. A local model needs a tool-enabled agent runtime; a text-only chat or bare model endpoint cannot run this workflow by itself.

The repository installer copies the canonical folder without symlinks. For a project installation, run from the repository:

```text
python tools/install_skill.py --host codex --project "ABSOLUTE_PROJECT_PATH"
python tools/install_skill.py --host claude --project "ABSOLUTE_PROJECT_PATH"
```

Codex project destination: `.agents/skills/ai-job-toolkit`. Claude Code project destination: `.claude/skills/ai-job-toolkit`. For user scope, replace `--project ...` with `--user`. The installer refuses to overwrite a different existing skill. Use `--destination` for another compatible agent's documented skill directory. A full installation source should be reviewed before enabling it.

Invoke `$ai-job-toolkit` in Codex or `/ai-job-toolkit` in Claude Code. A host that supports the Agent Skills format can load the folder using its own documented installation flow. If it doesn't, explicitly load `SKILL.md` and its needed references in a tool-enabled session; this is manual loading, not automatic discovery. Do not claim all ChatGPT interfaces can install or run local skills.

Official installation references checked during development:
- https://learn.chatgpt.com/docs/build-skills
- https://code.claude.com/docs/en/skills

The previous dashboard is archived under `legacy/dashboard` in the source repository. It uses a separate database and is not the skill's interface. The helper's generated HTML report reads the skill's actual workspace.
