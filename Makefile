default: test

testserver:
	ln -s ../../../combadge/target/x86_64-unknown-linux-musl/debug/combadge webapp/dist/assets/combadge
	python manage.py testserver

clean:
	rm -rf .env .ansible-env webapp/tmp/ webapp/node_modules/ webapp/bower_components/ static webapp/dist/assets/combadge
	find . -name "*.pyc" -delete

test:
	make -C webapp test

webapp:
	python manage.py frontend build

.PHONY: webapp
