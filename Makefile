default: test

testserver:
	poetry install
	.venv/bin/python manage.py testserver

clean:
	rm -rf .env .ansible-env webapp/tmp/ webapp/node_modules/ webapp/bower_components/ static
	find . -name "*.pyc" -delete

test:
	make -C webapp test

do_format:
	poetry run isort -rc unittests tests flask_app
	poetry run black unittests tests flask_app

check:
	poetry run isort -rc --check unittests tests flask_app
	poetry run black --check unittests tests flask_app
	poetry run pylint -j $(shell nproc) flask_app
	poetry run mypy flask_app/
	poetry run pytest unittests/

webapp:
	poetry install
	.venv/bin/python manage.py frontend build

.PHONY: webapp
