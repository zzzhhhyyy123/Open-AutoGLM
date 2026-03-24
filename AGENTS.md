# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

Open-AutoGLM (Phone Agent) is a Python CLI/library that automates mobile phones (Android/HarmonyOS/iOS) using a vision-language model. It is a pure Python package with no databases, web servers, or containers required for development. See `README.md` / `README_en.md` for full docs.

### Development commands

- **Install deps**: `pip install -r requirements.txt && pip install -e ".[dev]"`
- **Lint**: `ruff check .` (linter) / `ruff format --check .` (formatter)
- **Type check**: `mypy phone_agent/ --ignore-missing-imports`
- **Format check**: `black --check .`
- **Tests**: `pytest tests/` (no tests exist yet; exit code 5 = "no tests collected" is expected)
- **List apps (hello-world)**: `python3 main.py --list-apps`
- **CLI help**: `python3 main.py --help`

### Important caveats

- `python` is not on PATH; always use `python3`.
- Dev tool binaries (`pytest`, `black`, `mypy`, `ruff`) install to `/home/ubuntu/.local/bin`. Ensure `PATH` includes that directory: `export PATH="/home/ubuntu/.local/bin:$PATH"`.
- The application requires a connected mobile device (via ADB/HDC/WDA) and a running VLM API to execute actual phone automation tasks. In the cloud VM neither is available, so end-to-end agent runs cannot be tested. Core functionality can be verified by: importing the package, instantiating `PhoneAgent`, and running `--list-apps`.
- Pre-commit hooks are configured (`.pre-commit-config.yaml`) using ruff, typos, and pymarkdown. Run `pre-commit run --all-files` to check code style compliance.
- The existing codebase has formatting issues flagged by `ruff format` and `black`; these are pre-existing and not regressions.
