#!/bin/sh

echo "** Creating default DB and users"

mariadb -u root -p$MARIADB_ROOT_PASSWORD --execute \
"CREATE DATABASE IF NOT EXISTS $GF_DATABASE_NAME;
CREATE USER '$GF_DATABASE_USER'@'%' IDENTIFIED BY '$GF_DATABASE_PASSWORD';
GRANT ALL PRIVILEGES ON $GF_DATABASE_NAME.* TO '$GF_DATABASE_USER'@'%';"

echo "** Finished creating default DB and users"