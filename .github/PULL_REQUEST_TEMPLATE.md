# Pull Request Template — Urban Heat Mitigation Platform

## Description

Please include a summary of the change and which issue is fixed. Include relevant motivation and context.

Fixes #(issue)

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that alters existing API contract)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring (no functional changes)
- [ ] Test addition or improvement
- [ ] CI/CD or build configuration change
- [ ] Dependency update

## Component Affected

- [ ] Satellite data acquisition (STAC / Bhuvan)
- [ ] Spectral indices computation
- [ ] LST retrieval
- [ ] UHI detection
- [ ] ML prediction engine
- [ ] XAI / SHAP explainability
- [ ] Recommendation / optimization engine
- [ ] Scenario simulation
- [ ] Dashboard / frontend (React)
- [ ] Map visualization (MapLibre GL)
- [ ] API (FastAPI routes)
- [ ] Database (PostgreSQL / PostGIS)
- [ ] Task queue (Celery / Redis)
- [ ] Deployment (Docker / Nginx)
- [ ] Monitoring (Prometheus / Grafana / Loki)
- [ ] Documentation
- [ ] CI/CD (GitHub Actions)
- [ ] Tests
- [ ] Other: _________

## Checklist

### Code Quality

- [ ] My code follows the project coding style (Black / isort / ESLint / Prettier)
- [ ] I have added type hints for Python or TypeScript types
- [ ] I have added comprehensive docstrings / comments where necessary
- [ ] I have run linters and fixed all warnings
- [ ] My changes generate no new warnings or errors

### Testing

- [ ] I have added tests that prove my fix is effective or my feature works
- [ ] New and existing unit tests pass locally
- [ ] I have tested on real or synthetic satellite imagery
- [ ] I have verified numerical correctness of spectral / ML outputs
- [ ] I have checked edge cases (cloud cover, missing bands, empty regions)

### Documentation

- [ ] I have updated the README if needed
- [ ] I have updated API documentation (OpenAPI / docstrings)
- [ ] I have updated relevant docs in the docs/ directory
- [ ] I have added a changelog entry if applicable

### Performance

- [ ] My changes do not introduce significant performance regressions
- [ ] I have considered memory usage for large satellite scenes
- [ ] I have considered Celery task timeouts for long-running operations

### Security

- [ ] I have validated all user inputs (Pydantic models)
- [ ] I have checked for SQL injection and path traversal vulnerabilities
- [ ] I have not committed any secrets, API keys, or credentials
- [ ] I have reviewed data access permissions for new endpoints

## How Has This Been Tested?

Describe the tests you ran to verify your changes. Provide instructions for reproduction.

- [ ] Unit tests: pytest tests/path/to/test_file.py
- [ ] Integration tests: pytest tests/integration/
- [ ] Manual testing: [Describe steps]
- [ ] Performance benchmark: [Attach results if applicable]

## Screenshots (if applicable)

Add screenshots to help explain your changes, especially for UI or map-related changes.

## Performance Checklist (if applicable)

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Inference time (ms) | | | |
| Memory usage (MB) | | | |
| Test count | | | |

## Additional Notes

Add any additional information that reviewers should know.

---

By submitting this pull request, I confirm that:
- I have read the contributing guidelines
- My code is licensed under the same license as this project (MIT)
- I have the right to contribute this code
