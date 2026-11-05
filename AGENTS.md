# Maintaining AI Job Toolkit

The product is the installable skill at `skills/ai-job-toolkit`. Keep host-independent instructions there. `agents/openai.yaml` is optional Codex UI metadata. Do not convert the core into a standalone model client or make the legacy dashboard a dependency.

Personal state belongs in an explicit private workspace, never in the skill or Git. Do not import the author's prior profile. Preserve valid user authorization without expanding its scope. Submission intent, browser execution and observed confirmation are separate events.

When changing Python behavior, run `python -m unittest discover -s tests -v`. Package with `python tools/package_skill.py`. Keep generated installations, `dist`, runtime data and caches ignored. Tests use synthetic data and must not contact employers or submit real applications.

The previous standalone app is archived at `legacy/dashboard`. It is not integrated with the skill database. Any UI work should read the skill's canonical state or use the existing report helper.
