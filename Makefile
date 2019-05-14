IMAGE := getslash/scotty
VERSION := 2.2.0

default: test

testserver:
	python manage.py testserver

clean:
	rm -rf .env .ansible-env webapp/tmp/ webapp/node_modules/ webapp/bower_components/ static
	find . -name "*.pyc" -delete

test:
	make -C webapp test

image:
	docker build -t ${IMAGE}:${VERSION} -f docker/Dockerfile .
	docker tag ${IMAGE}:${VERSION} ${IMAGE}:latest

push-image:
	docker push ${IMAGE}:${VERSION}
	docker push ${IMAGE}:latest

webapp:
	python manage.py frontend build

.PHONY: webapp
