FROM ubuntu:16.04


ADD ./frontend /src/webapp/dist
ADD ./transporter/transporter /usr/bin/transporter
ADD ./combadge_linux/combadge /src/webapp/dist/assets/combadge_linux
ADD ./combadge_mac/combadge /src/webapp/dist/assets/combadge_mac
ADD ./combadge_windows/combadge.exe /src/webapp/dist/assets/combadge_windows.exe


ENV PYTHON_VERSION 3.6
ENV PYTHON_EXECUTABLE python$PYTHON_VERSION

ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8


RUN apt-get update && apt-get -y install build-essential rsync software-properties-common libpq-dev nginx curl redis-server gcc sudo uuid-runtime squashfs-tools libxslt-dev libxml2-dev sshpass libsasl2-dev libldap2-dev git


# nginx
RUN add-apt-repository ppa:chris-lea/nginx-devel
RUN apt-get update
RUN apt-get -y install nginx
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update
RUN apt-get install -y $PYTHON_EXECUTABLE $PYTHON_EXECUTABLE-dev $PYTHON_EXECUTABLE-venv
RUN ln -s /usr/bin/$PYTHON_EXECUTABLE /usr/local/bin/python
RUN ln -s /usr/bin/$PYTHON_EXECUTABLE /usr/local/bin/python3

RUN curl https://bootstrap.pypa.io/get-pip.py | $PYTHON_EXECUTABLE
RUN $PYTHON_EXECUTABLE -m pip install requests virtualenv
RUN echo $PYTHON_EXECUTABLE

# dockerize
ENV DOCKERIZE_VERSION v0.3.0
RUN curl -L https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz | tar xz -C /usr/local/bin


VOLUME /conf
VOLUME /uploads

ADD ./manage.py ./src/
ADD ./etc ./src/etc
ADD ./_lib ./src/_lib
ADD ./deps/ ./src/deps
ADD ./flask_app ./src/flask_app
ADD ./migrations ./src/migrations

RUN echo $PYTHON_EXECUTABLE
RUN cd ./src && DISABLE_PIP_CACHE=1 $PYTHON_EXECUTABLE manage.py bootstrap --app


ADD ./frontend /src/webapp/dist
ADD ./transporter/transporter /usr/bin/transporter
ADD ./combadge_linux/combadge /src/webapp/dist/assets/combadge_linux
ADD ./combadge_mac/combadge /src/webapp/dist/assets/combadge_mac
ADD ./combadge_windows/combadge.exe /src/webapp/dist/assets/combadge_windows.exe

RUN rm -rf ../etc/nginx/conf.d/*
RUN rm -f ../etc/nginx/sites-enabled/*

EXPOSE 80 443

WORKDIR /src
