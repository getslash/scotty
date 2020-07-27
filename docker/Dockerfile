FROM ekidd/rust-musl-builder as rust-builder
ADD ./transporter/ ./transporter
ADD ./combadge/ ./combadge
RUN sudo chown -R rust:rust .
RUN cd transporter && cargo build --release
RUN cd combadge && cargo build --release

FROM node:12 as frontend-builder
# build frontend
RUN npm install -g ember-cli
ADD ./webapp/ ./frontend/
RUN cd ./frontend/ && yarn install
RUN cd ./frontend/ && node_modules/.bin/ember build --environment production

FROM python:3.7

ENV POETRY_VERSION=1.0.3

# nginx
RUN apt-get update && apt-get -y install build-essential rsync software-properties-common libpq-dev nginx curl redis-server gcc sudo uuid-runtime squashfs-tools libxslt-dev libxml2-dev sshpass libsasl2-dev libldap2-dev git

ADD ./pyproject.toml ./src/
ADD ./poetry.lock ./src/
RUN pip install "poetry==$POETRY_VERSION"
RUN poetry config virtualenvs.in-project true
RUN cd ./src && poetry install

# dockerize
ENV DOCKERIZE_VERSION v0.3.0
RUN curl -L https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz | tar xz -C /usr/local/bin

VOLUME /conf
VOLUME /uploads

ADD ./manage.py ./src/
ADD ./etc ./src/etc
ADD ./_lib ./src/_lib
ADD ./flask_app ./src/flask_app
ADD ./migrations ./src/migrations

COPY $COMBADGE_DIR ./src/
RUN sudo chmod 755 ./src/combadge_assets/v2/combadge_linux/combadge
RUN sudo chmod 755 ./src/combadge_assets/v2/combadge_darwin/combadge

COPY --from=frontend-builder /frontend/dist /src/webapp/dist
COPY --from=rust-builder /home/rust/src/transporter/target/x86_64-unknown-linux-musl/release/transporter /usr/bin/transporter
COPY --from=rust-builder /home/rust/src/combadge/target/x86_64-unknown-linux-musl/release/combadge /src/webapp/dist/assets

RUN rm -rf ../etc/nginx/conf.d/*
RUN rm -f ../etc/nginx/sites-enabled/*

EXPOSE 80 443

WORKDIR /src
