PATHS = setup.py workstate/ tests/

help:
	@echo  "WorkState dev makefile"
	@echo  ""
	@echo  "usage: make <target>"
	@echo  " up	Updates dev/test dependencies"
	@echo  " deps	Ensure dev/test dependencies are installed"
	@echo  " test	Runs all tests"
	@echo  " lint	Reports all linter violations"
	@echo  " ci	Runs lints & tests (as a full CI run would)"
	@echo  " pretty Tries to auto-fix simpler linting issues"

up:
	pip-compile -qU tests/requirements.in
	pip-sync tests/requirements.txt

deps:
	@which pip-sync > /dev/null || pip install pip-tools
	pip-sync -q tests/requirements.txt

test:
	green

_lint:
	flake8 ${PATHS}
	mypy ${PATHS}
	pylint ${PATHS}

pretty: deps
	isort ${PATHS}

lint: deps pretty _lint

ci: deps _lint test
