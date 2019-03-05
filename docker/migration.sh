#!/bin/bash -ex

TARGET=scotty-staging.lab.il.infinidat.com

as_root() {
    ssh $TARGET -l root $*;
}

as_scotty() {
    ssh $TARGET -l scotty $*;
}

echo Checking connectivity
as_root uptime
as_scotty uptime

echo Installing docker...
as_root sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common python-pip
as_root "curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add -"
as_root 'add-apt-repository -y "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable"'
as_root 'apt-get update'
as_root 'apt-get install -y docker-ce'

echo Install docker-compose
as_root 'which docker-compose || pip install -U docker-compose'

echo Archiving old source...
as_scotty "(test -d /opt/scotty/src && (mv /opt/scotty/src /opt/scotty/_old_src)) || true"

echo Copying docker-compose file
as_root "test -d /opt/scotty/docker || mkdir /opt/scotty/docker"
scp * root@$TARGET:/opt/scotty/docker/

echo Migrating Infinilab Token and SSH keys
as_root mkdir -p /root/.infinidat
as_root cp /home/scotty/.infinidat/infinilab.tkn /root/.infinidat/infinilab.tkn
as_root cp /home/scotty/.ssh/infradev-id_rsa /root/.ssh/infradev-id_rsa
as_root chown -R root: /root/.infinidat /root/.ssh/infradev-id_rsa
as_root chmod 400 /root/.ssh/infradev-id_rsa

echo Creating systemd unit
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

echo Updating systemd
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

echo Pulling images...
as_root "cd /opt/scotty/docker && docker-compose -f docker-compose.yml pull"

echo Shutting down nginx...
as_root systemctl stop nginx scotty-celery-beat scotty-celery-worker scotty-wsgi
as_root systemctl disable nginx scotty-celery-beat scotty-celery-worker scotty-wsgi

echo Migrating DB
as_root "cd /opt/scotty/docker && docker-compose -p scotty up -d db"
sleep 10
as_root docker exec -u postgres scotty_db_1 dropdb scotty
as_root docker exec -u postgres scotty_db_1 createdb -E utf8 scotty
as_root "time ((sudo -u postgres pg_dump -w -Fc scotty) | docker exec -u postgres -i scotty_db_1 pg_restore -Fc -d scotty -w -v)"


as_root "cd /opt/scotty/docker && docker-compose -p scotty down"
as_root "systemctl start scotty-docker"
as_root "systemctl enable scotty-docker"
