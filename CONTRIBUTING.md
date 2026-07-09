# Contributing to Urban Heat Mitigation Platform

Thank you for your interest in contributing to the Urban Heat Mitigation
Platform! We welcome contributions from everyone — whether you are fixing a bug,
adding a feature, improving documentation, or proposing new ideas.

Please take a moment to review this guide to make the process smooth and
effective for everyone involved.

## Code of Conduct

This project and everyone participating in it is governed by the
[Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to
uphold this code. Please report unacceptable behavior to
conduct@urbanheatmitigation.org.

## Getting Started

### 1. Fork the Repository

Fork the repository on GitHub and clone your fork locally:

```bash
git clone https://github.com/<your-username>/urbanheat-mitigation-platform.git
cd urbanheat-mitigation-platform
git remote add upstream https://github.com/urbanheat/urbanheat-mitigation-platform.git
```

### 2. Branch Naming Convention

Create a branch with a descriptive name following this convention:

| Prefix     | Purpose                          | Example                                 |
| ---------- | -------------------------------- | --------------------------------------- |
| `feature/` | New features                     | `feature/sentinel-3-integration`        |
| `fix/`     | Bug fixes                        | `fix/lst-water-vapor-correction`        |
| `docs/`    | Documentation changes            | `docs/api-endpoint-examples`            |
| `refactor/`| Code refactoring                 | `refactor/ml-pipeline-modularization`   |
| `test/`    | Adding or updating tests         | `test/uhi-hotspot-statistical-validity` |
| `chore/`   | Maintenance tasks                | `chore/update-dependencies`             |
| `ci/`      | CI/CD configuration changes      | `ci/add-gpu-runner-workflow`            |

```bash
git checkout -b feature/your-feature-name
```

### 3. Keep Your Fork Updated

Regularly sync your fork with the upstream repository:

```bash
git fetch upstream
git rebase upstream/main
```

## Development Setup

### Prerequisites

| Tool         | Version     | Installation                                        |
| ------------ | ----------- | --------------------------------------------------- |
| Python       | 3.11+       | [python.org](https://www.python.org/downloads/)     |
| Node.js      | 20 LTS      | [nodejs.org](https://nodejs.org/)                   |
| Docker       | 24+         | [docker.com](https://www.docker.com/products/docker-desktop) |
| Docker Compose | 2.20+    | Ships with Docker Desktop                           |
| Git          | 2.40+       | [git-scm.com](https://git-scm.com/)                 |

### Local Development

#### Backend (Python)

```bash
# Create and activate virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Copy environment file
cp .env.example .env
```

#### Frontend (TypeScript/React)

```bash
cd frontend
cp .env.example .env
npm install
```

#### Infrastructure (Docker)

```bash
# Start supporting services (PostgreSQL, Redis, etc.)
docker compose -f docker-compose.dev.yml up -d

# Run database migrations
alembic upgrade head

# Seed sample data (optional)
python scripts/seed_data.py
```

### Running Locally

```bash
# Terminal 1: Backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Celery worker
celery -A app.tasks worker --loglevel=info

# Terminal 3: Frontend
cd frontend && npm run dev
```

The application will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:5173

## Code Style

We use automated tools to enforce consistent code style. Please ensure your
code passes all checks before submitting a pull request.

### Python

| Tool    | Purpose                     | Command                       |
| ------- | --------------------------- | ----------------------------- |
| [Black](https://black.readthedocs.io/) | Code formatter (88 char line width) | `black .`           |
| [Ruff](https://ruff.rs/)             | Linter and import sorter    | `ruff check . --fix`          |
| [MyPy](https://mypy-lang.org/)       | Static type checking        | `mypy app/`                   |

Run all Python checks with:

```bash
black . && ruff check . --fix && mypy app/
```

### TypeScript / React

| Tool      | Purpose                     | Command                       |
| --------- | --------------------------- | ----------------------------- |
| [ESLint](https://eslint.org/)    | Linter                      | `npm run lint`                |
| [Prettier](https://prettier.io/) | Code formatter              | `npm run format`              |

Run all frontend checks with:

```bash
cd frontend && npm run lint && npm run format
```

### Pre-commit Hooks

We use [pre-commit](https://pre-commit.com/) to automatically run checks before
each commit. Install the hooks with:

```bash
pre-commit install
```

The pre-commit configuration runs:
- Trailing whitespace removal
- EOF newline fixing
- YAML and JSON validation
- Black formatting
- Ruff linting
- MyPy type checking

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/) v1.0.0:

```
<type>(<scope>): <short-description>

<body>

<footer>
```

### Types

| Type       | Usage                                 |
| ---------- | ------------------------------------- |
| `feat`     | A new feature                         |
| `fix`      | A bug fix                             |
| `docs`     | Documentation only changes            |
| `style`    | Code formatting (no logic change)     |
| `refactor` | Code restructuring (no behavior change)|
| `perf`     | Performance improvement               |
| `test`     | Adding or updating tests              |
| `chore`    | Build process or tooling changes      |
| `ci`       | CI/CD pipeline changes                |

### Scope (Optional)

Recommended scopes: `satellite`, `lst`, `indices`, `uhi`, `features`, `ml`,
`xai`, `recommendations`, `scenarios`, `api`, `dashboard`, `map`, `auth`,
`db`, `docker`, `docs`, `config`

### Examples

```
feat(ml): add CatBoost regressor with GPU support

Implement CatBoost with ordered boosting for categorical features.
GPU training enabled via `task_type='GPU'` parameter.

Closes #142
```

```
fix(lst): correct water vapor scaling in split-window algorithm

The water vapor correction factor was incorrectly normalized,
causing 2-3K overestimation in tropical regions.

Fixes #89
```

```
docs(api): add OpenAPI examples for scenario simulation endpoint
```

## Pull Request Process

### Before Submitting

1. Ensure all code style checks pass (see [Code Style](#code-style) above).
2. Ensure all tests pass (see [Testing](#testing) below).
3. Write or update tests for any changed functionality.
4. Update documentation for any changed API or behavior.
5. Rebase your branch on the latest `main`:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```
6. Resolve any merge conflicts.

### PR Template

All pull requests must use the provided [pull request template](.github/PULL_REQUEST_TEMPLATE.md).
Fill in all relevant sections with complete information.

### Submission

1. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
2. Open a pull request from your fork to the `main` branch of the upstream
   repository.
3. Link any related issues using GitHub keywords (`Closes #123`, `Fixes #456`).
4. Request review from at least one maintainer.
5. Add the appropriate labels (`bug`, `enhancement`, `documentation`, etc.).

### Review Process

1. A maintainer will review your PR within **3–5 business days**.
2. Automated CI checks must pass (lint, type-check, test, build, security scan).
3. Reviewers may request changes. Please address feedback promptly.
4. Once approved, a maintainer will **squash-merge** your PR into `main`.
5. The commit message will be formatted as `type(scope): description (#PR)`.

### After Merge

- Delete your feature branch after the PR is merged.
- Celebrate your contribution! :tada:

## Testing

All tests must pass before a pull request can be merged. We enforce a minimum
code coverage threshold of **85%** for the backend and **75%** for the frontend.

### Backend Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_lst_retrieval.py

# Run tests matching a keyword
pytest -k "uhi or lst"

# Run with verbose output
pytest -v

# Run property-based tests only
pytest -k "hypothesis" --hypothesis-show-statistics
```

### Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run in watch mode
npm test -- --watch

# Run specific test file
npm test -- Button.test.tsx
```

### Integration Tests

```bash
# Start services
docker compose -f docker-compose.test.yml up -d

# Run integration tests
pytest tests/integration/

# Run end-to-end workflow test
pytest tests/e2e/test_satellite_to_dashboard.py
```

## Documentation Requirements

All contributions must include appropriate documentation:

1. **Code Documentation**: Write clear docstrings for all public modules, classes,
   and functions using Google-style docstrings.

2. **API Documentation**: All new or modified API endpoints must include Pydantic
   models with field descriptions and examples. Auto-generated OpenAPI docs will
   pick these up automatically.

3. **README Updates**: If your change affects setup, usage, or architecture,
   update the relevant sections in `README.md`.

4. **Changelog**: Add a summary of your change under the `[Unreleased]` section
   in `CHANGELOG.md`. Follow the existing format.

5. **Architecture Decision Records**: For significant architectural changes,
   create an ADR in `docs/adr/` explaining the context, decision, and
   consequences.

## Questions?

If you have questions about contributing, please:

- Open a [discussion](https://github.com/urbanheat/urbanheat-mitigation-platform/discussions)
- Join our community chat (link TBD)
- Email the maintainers at maintainers@urbanheatmitigation.org

We look forward to your contributions!
