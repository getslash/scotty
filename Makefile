default: test

testserver:
	poetry install
	.venv/bin/python manage.py testserver

clean:
	rm -rf .env .ansible-env webapp/tmp/ webapp/node_modules/ webapp/bower_components/ static
	find . -name "*.pyc" -delete

test:
	make -C webapp test

webapp:
	poetry install
	.venv/bin/python manage.py frontend build

.PHONY: webapp
