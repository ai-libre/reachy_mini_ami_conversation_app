# Repository Information

**Created:** 2025-11-22 14:28:52 UTC
**Last Updated:** 2025-11-22 14:28:52 UTC

## Repository Details

**Name:** reachy_mini_ami_conversation_app
**Organization:** pollen-robotics
**URL:** https://github.com/pollen-robotics/reachy_mini_ami_conversation_app
**Primary Language:** Python
**License:** (Check LICENSE file in repository)

## Current Branch Status

**Active Branch:** `claude/create-ai-docs-structure-013G89HT6DEXLKB1M8cTfE2P`
**Status:** Clean (no uncommitted changes at session start)

### Recent Commits

```
e5e0ca4 - Fixed BGR2RGB when sending image to gradio
8097829 - Merge pull request #110: small-readme-update
ff4f147 - Add note about uv.lock file
247a1fb - Merge pull request #109: deps-refresh-uv-upgrade
5c54619 - chore: update uv.lock file
```

## Project Structure

```
reachy_mini_ami_conversation_app/
├── .github/
│   └── workflows/           # CI/CD automation
│       ├── lint.yml
│       ├── typecheck.yml
│       └── test.yml
│
├── docs/
│   ├── assets/              # Images, diagrams
│   └── scheme.mmd           # Architecture diagram (Mermaid)
│
├── src/reachy_mini_conversation_app/
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration
│   ├── openai_realtime.py   # OpenAI handler
│   ├── moves.py             # Movement system
│   ├── camera_worker.py     # Camera processing
│   ├── console.py           # Console mode
│   ├── audio/               # Audio processing
│   ├── tools/               # Tool implementations
│   ├── vision/              # Vision processing
│   ├── profiles/            # AI personalities
│   └── prompts/             # Prompt templates
│
├── tests/                   # Unit tests
│   ├── conftest.py
│   ├── test_openai_realtime.py
│   └── audio/
│
├── .env.example             # Environment template
├── pyproject.toml           # Project metadata
├── uv.lock                  # Locked dependencies
├── README.md                # Main documentation
└── _ai/                     # AI-generated docs (this folder!)
    ├── docs/                # Technical documentation
    ├── refs/                # References and resources
    ├── repos/               # Repository information
    └── explorations/        # Analysis and explorations
```

## Build System

**Package Manager:** uv (recommended) or pip
**Build Backend:** hatchling
**Python Version:** >=3.10 (3.12.1 recommended)

### Package Metadata

```toml
[project]
name = "reachy-mini-conversation-app"
version = "0.1.0"
description = "Realtime conversation app for Reachy Mini robot"
readme = "README.md"
requires-python = ">=3.10"
```

### Entry Points

```toml
[project.scripts]
reachy-mini-conversation-app = "reachy_mini_conversation_app.main:main"
```

## Dependencies

### Core Runtime
- openai (>=2.1)
- fastrtc (>=0.0.33)
- gradio (>=5.49.0)
- aiortc (>=1.13.0)
- opencv-python (>=4.12.0.88)
- librosa (>=0.10.0)
- reachy_mini (>=1.0.0.rc4)

### Optional Extras

**`all_vision`** (YOLO + local VLM):
- torch (>=2.7.0)
- transformers (>=4.47.1)
- ultralytics (>=8.3.0)
- supervision (>=0.27.0)

**`mediapipe_vision`**:
- mediapipe (>=0.10.0)

**`dev`** (development tools):
- pytest
- pytest-asyncio
- ruff
- mypy

### Installation Commands

```bash
# Full installation with all vision features
uv sync --extra all_vision --group dev

# Basic installation
uv sync

# Development only
uv sync --group dev
```

## CI/CD Pipelines

### GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **lint.yml** | Push, PR | Run ruff linter |
| **typecheck.yml** | Push, PR | Run mypy type checking |
| **test.yml** | Push, PR | Run pytest suite |

### Quality Gates

- ✅ All tests must pass
- ✅ No type errors (mypy)
- ✅ No linting errors (ruff)
- ✅ Code formatted (ruff format)

## Development Workflow

### Setup

```bash
# Clone repository
git clone https://github.com/pollen-robotics/reachy_mini_ami_conversation_app.git
cd reachy_mini_ami_conversation_app

# Create virtual environment
uv venv --python 3.12.1
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Install dependencies
uv sync --extra all_vision --group dev

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_openai_realtime.py

# With coverage
pytest --cov=src/reachy_mini_conversation_app

# Async tests
pytest -v tests/test_openai_realtime.py  # pytest-asyncio handles this
```

### Code Quality

```bash
# Lint
ruff check .

# Format
ruff format .

# Type check
mypy src/reachy_mini_conversation_app

# All quality checks
ruff check . && ruff format . && mypy src/
```

### Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Branching Strategy

**Main Branch:** (likely `main` or `master`)
**Feature Branches:** `claude/` prefix for AI-generated work
**Current Branch:** `claude/create-ai-docs-structure-013G89HT6DEXLKB1M8cTfE2P`

### Recommended Git Commands

```bash
# Create feature branch
git checkout -b feature/my-feature

# Commit changes
git add .
git commit -m "feat: add new feature"

# Push to remote
git push -u origin feature/my-feature

# Create pull request (use GitHub UI or gh CLI)
gh pr create --title "Add new feature" --body "Description"
```

## Issue Tracking

**Platform:** GitHub Issues
**URL:** https://github.com/pollen-robotics/reachy_mini_ami_conversation_app/issues

### Label Categories (typical)
- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Documentation improvements
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention needed

## Pull Request Guidelines

1. **Fork & Branch:** Create a feature branch from main
2. **Test:** Ensure all tests pass
3. **Lint:** Run ruff and mypy
4. **Commit:** Use conventional commits (feat:, fix:, docs:, etc.)
5. **PR:** Provide clear description and context
6. **Review:** Address review comments
7. **Merge:** Squash or merge based on project preference

## Versioning

**Scheme:** Semantic Versioning (SemVer)
**Current:** 0.1.0 (pre-release)

**Version Format:** MAJOR.MINOR.PATCH
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md (if exists)
3. Create git tag: `git tag -a v0.2.0 -m "Release v0.2.0"`
4. Push tag: `git push origin v0.2.0`
5. GitHub Actions may auto-publish to PyPI (check workflows)

## Contributing

### How to Contribute

1. **Report Issues:** Use GitHub Issues with clear reproduction steps
2. **Suggest Features:** Open issue with `enhancement` label
3. **Submit Code:** Fork, branch, commit, PR
4. **Improve Docs:** Documentation PRs always welcome

### Code Style

- **PEP 8** compliance (enforced by ruff)
- **Type hints** everywhere (checked by mypy)
- **Docstrings** for public APIs
- **Tests** for new features

## Community

**Maintainer:** Pollen Robotics team
**Contact:** (Check repository for contact info)
**Discord/Slack:** (Check pollen-robotics.com for community links)

## Project Status

**Stage:** Active Development
**Stability:** Beta / Release Candidate
**Production Ready:** ⚠️ Check with maintainers

### Known Limitations

- Requires OpenAI API key (paid service)
- Hardware-dependent (Reachy Mini robot)
- GPU recommended for local vision

## Roadmap

(Check repository issues/projects for current roadmap)

Likely priorities:
- [ ] Improved face tracking accuracy
- [ ] Additional dance moves
- [ ] More AI profiles
- [ ] Multi-language support
- [ ] Performance optimizations

## Documentation

**Primary:** README.md in repository root
**Architecture:** docs/scheme.mmd (Mermaid diagram)
**API:** Code docstrings + type hints
**AI Docs:** This `_ai/` folder!

---

**Quick Links:**
- [Repository](https://github.com/pollen-robotics/reachy_mini_ami_conversation_app)
- [Issues](https://github.com/pollen-robotics/reachy_mini_ami_conversation_app/issues)
- [Pull Requests](https://github.com/pollen-robotics/reachy_mini_ami_conversation_app/pulls)
- [Pollen Robotics](https://pollen-robotics.com/)

This repository represents a **cutting-edge integration** of AI, robotics, and multimodal interaction for the Reachy Mini platform.
