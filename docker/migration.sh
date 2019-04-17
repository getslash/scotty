#!/bin/bash

set -ex

TARGET=scotty-telad-01.telad.il.infinidat.com

as_root() {
    ssh $TARGET -l root $*;
}

as_scotty() {
    ssh $TARGET -l scotty $*;
}

echo -------- Checking connectivity --------
as_root uptime
as_root 'mkdir ~scotty/.ssh && cp ~/.ssh/authorized_keys ~scotty/.ssh/authorized_keys && chown -R scotty: ~scotty/.ssh'
as_scotty uptime

echo -------- Installing docker --------
as_root 'apt-get update'
as_root 'apt-get install -y apt-transport-https ca-certificates curl gnupg2 software-properties-common python-pip'
as_root 'curl -fsSL https://download.docker.com/linux/debian/gpg | sudo apt-key add -'
as_root 'add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable"'
as_root 'apt-get update'
as_root 'apt-get install -y docker-ce docker-ce-cli containerd.io'

echo -------- Install docker-compose --------
as_root 'which docker-compose || pip install -U docker-compose'

echo  -------- Archiving old source --------
as_scotty "(test -d /opt/scotty/src && (mv /opt/scotty/src /opt/scotty/_old_src)) || true"

echo -------- Copying docker-compose file --------
as_root "test -d /opt/scotty/docker || mkdir /opt/scotty/docker"
scp docker/* root@$TARGET:/opt/scotty/docker/

echo -------- Creating systemd unit --------
as_root "cat > /lib/systemd/system/scotty-docker.service" << EOF
[Unit]
Description=Scotty
Requires=docker.service
After=docker.service

[Service]
WorkingDirectory=/opt/scotty/docker
Type=simple
RemainAfterExit=True
ExecStart=/usr/local/bin/docker-compose -f docker-compose.yml -p scotty up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.yml -p scotty stop

[Install]
WantedBy=multi-user.target

EOF

echo -------- Updating systemd --------
as_root systemctl daemon-reload

echo Logging in to docker...
ssh -tt root@$TARGET "test -d ~/.docker || mkdir ~/.docker"
as_root "cat > ~/.docker/config.json" <<EOF
{
        "auths": {
                "git.infinidat.com:4567": {
                        "auth": "cm9leWQ6WTBnYUZpcmUh"
                }
        }
}
EOF

echo -------- Pulling images --------
as_root "cd /opt/scotty/docker && docker-compose -f docker-compose.yml pull"

echo -------- Shutting down nginx... --------
as_root systemctl stop nginx scotty-celery-beat scotty-celery-worker scotty-wsgi transporter
as_root systemctl disable nginx scotty-celery-beat scotty-celery-worker scotty-wsgi transporter

echo -------- Migrating DB --------
as_root "sed -i 's/SQLALCHEMY_DATABASE_URI/#SQLALCHEMY_DATABASE_URI/g' /opt/scotty/conf.d/001-deployment_conf.yml"
as_root "cd /opt/scotty/docker && docker-compose -p scotty up -d db"
sleep 10
as_root docker exec scotty_db_1 dropdb -U scotty scotty
as_root docker exec scotty_db_1 createdb -E utf8 -U scotty scotty
as_root "cd / && time ((sudo -u postgres pg_dump -w -Fc scotty) | docker exec -i scotty_db_1 pg_restore -Fc -U scotty -w -d scotty --no-acl --no-owner)"

as_root "cd /opt/scotty/docker && docker-compose -p scotty down"
as_root "systemctl start scotty-docker"
as_root "systemctl enable scotty-docker"
