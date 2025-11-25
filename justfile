app := "uwhoisd"
docker_repo := "ghcr.io/kgaughan/" + app

[private]
default:
	@just --list

# setup virtual environment
devel:
	@uv sync --frozen

# tidy everything with ruff
tidy:
	@uv run --frozen ruff check --fix

# run the test suite
tests:
	@uv run --frozen pytest

# run the typechecker
typecheck:
	@uv run --frozen mypy src

# clean up any caches or temporary files and directories
clean:
	@rm -rf .mypy_cache .pytest_cache .ruff_cache .venv dist htmlcov .coverage
	@find . -name \*.orig -delete

# build the docker image
docker:
	@rm -rf dist
	@uv build --wheel
	@docker buildx build -t {{docker_repo}}:$(git describe --tags --always) .
	@docker tag {{docker_repo}}:$(git describe --tags --always) {{docker_repo}}:latest
