# AI in Research: homework

Homework for **AI in Research** (UCLA EPSS 254, Fall 2026). Students, auditors and faculty are all welcome to submit.

## How it works

Each week's assignment lives in its own folder. You work on it with an AI coding agent, then submit it as a pull request from your fork, into `week-<n>/submissions/<your-github-username>/`. Every pull request is checked automatically.

To start any week, open the week's folder below, or its page on [class.xhelio.ai](https://class.xhelio.ai). You'll find a one-line prompt to give your AI agent there.

## Weeks

| Week | Assignment | Due |
|---|---|---|
| [1](week-1/) | The hardest task in your field, as an AI benchmark task | Wed Oct 7, before class |

## Rules

- Change only files under `week-<n>/submissions/<your-github-username>/`.
- Never commit API keys or tokens. Only use data you may share publicly.
- Say in your pull request which AI helped you, and how.

## Under the hood

- [`tools/`](tools/): `uv run tools/hw.py`, the checklist your agent follows, and the checks CI runs on every pull request
- [`.agents/skills/build-a-task/SKILL.md`](.agents/skills/build-a-task/SKILL.md): the guide your AI agent reads

## License

[MIT](LICENSE). By opening a pull request you license your submission under MIT.
