clean_coverage:
	rm -f .coverage
	rm -rf htmlcov

clean_cache:
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf **/__pycache__

clean: clean_coverage clean_cache

test: clean_coverage
	k=$(filter-out $@,$(MAKECMDGOALS)); \
if [ -n "$k" ]; then \
	( \
		source .venv/bin/activate; \
		coverage run -m pytest -xsvv -k $k; \
	) \
else \
	( \
		source .venv/bin/activate; \
		coverage run -m pytest -xsvv; \
    ) \
fi

report: test
	coverage html && open htmlcov/index.html

format:
	black . && isort .

install: clean_cache
	( \
		source .venv/bin/activate; \
		pip install --upgrade pip; \
		pip install -r requirements.txt; \
	)

upgrade:
	( \
		source .venv/bin/activate; \
		pip --disable-pip-version-check list --outdated --format=json | python -c "import json, sys; print('\n'.join([x['name'] for x in json.load(sys.stdin)]))" | xargs -n1 pip install -U; \
	)

run:
	( \
		source .venv/bin/activate; \
		python chess.py; \
	)