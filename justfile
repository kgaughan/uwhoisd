app := "uwhoisd"
docker_repo := "ghcr.io/kgaughan/" + app

[private]
default:
	@just --list

# setup virtual environment
devel:
	@uv sync --frozen

# tidy everything with ruff
[group("Analysis/Fixing")]
tidy:
	@uv run --frozen ruff check --fix

# run the test suite
[group("Testing")]
tests:
	@uv run --frozen pytest

# run the tests with coverage
[group("Testing")]
coverage:
	@uv run --frozen pytest --cov={{app}} --cov-report=html --cov-report=term

# run the typechecker
[group("Analysis/Fixing")]
typecheck:
	@uv run --frozen mypy src

# clean up any caches or temporary files and directories
clean:
	@rm -rf .mypy_cache .pytest_cache .ruff_cache .venv dist htmlcov .coverage tests/results.xml .coverage.*
	@find . -name \*.orig -delete

# build the docker image
docker:
	@rm -rf dist
	@uv build --wheel
	@docker buildx build -t {{docker_repo}}:$(git describe --tags --always) .
	@docker tag {{docker_repo}}:$(git describe --tags --always) {{docker_repo}}:latest
