# BackupBot - Python Backup Tool for Linux Container Environments

Python command line tool to back up complete Linux Container systems.

Current features:

- back up `docker-compose` bind mounts, volumes and MySQL dumps:
  - create a folder structure which resembles the system structure
  - create tar-balls (bind mounts and volumes) and mysqldumps (MySQL databases)

Planned features:

- keep N amount of backups or only keep backups from a certain time period
- mirror created backup folder structure on network storage via SMB or rsync
- command to run (`docker-compose`-) system using backup files / restart single running components using backups

Currently, only `docker-compose`-based systems are supported. The project in general is **WIP**.


----------------------------------

## Usage
Assume the setup found in `doc/example/manual_test`:
```
service/
    |-docker-compose.yaml
    |-scripts/
    |    |-example_script.sh
```

Additionally there is an external volume containing text files (these are served by a Python HTTP server - you need to create it yourself):
```
docker volume create http_server_test_volume
```

... and fill it with arbitrary files.

`docker-compose.yaml`:

```yaml
version: '3'

services:
  http-server:
    image: python:latest
    container_name: http-server
    hostname: http-server
    command: sh -c "python -m http.server 8000 --directory /data"
    ports:
      - 8000:8000
    volumes:
      - http_server_test_volume:/data
      - ./bind_mount:/config

  database-service:
    image: mysql:latest
    hostname: database-service
    container_name: datatbase-service
    environment:
    - MYSQL_ROOT_PASSWORD=root_password
    - MYSQL_USER=user
    - MYSQL_PASSWORD=user_password
    - MYSQL_DATABASE=test_database

volumes:
  http_server_test_volume:
    external: true
```

To backup the docker-compose system, create a backup config file (e.g. `backup-config.json`) like so:

```json
{
    "http-server": [
        {
            "type": "bind_mount_backup",
            "config": {
                "bind_mounts": [
                    "scripts"
                ]
            }
        },
        {
            "type": "volume_backup",
            "config": {
                "volumes": [
                    "http_server_test_volume"
                ]
            }
        }
    ],
    "database-service": [
        {
            "type": "mysql_backup",
            "config": {
                "database": "test_database",
                "user": "root",
                "password": "root_password"
            }
        }
    ]
}

```

Then run `backupbot` in `doc/example/manual` via the command line:

```shell
backupbot -r service/ docker-compose backup/ backup-config.json
```

`doc/example/manual/backup` after backup:
```
backup_directory
    |-http-server
    |   |-bind_mounts
    |   |   |-scripts
    |   |   |   |-TIMESTAMP-http-server.tar.gz
    |   |-volumes
    |   |   |-http_server_test_volume
    |   |   |   |-TIMESTAMP-http_server_test_volume.tar.gz
    |-database-service
    |   |-mysql_databases
    |   |   |-test_database
    |   |   |   |-TIMESTAMP-test_database.sql
```

---------------------------------------------

## Manual

`backupbot` allows to define "backup tasks" for each service in a `docker-compose` system. The tasks that are run for each service are defined in a config file in JSON format. Each task needs certain configuration parameters to work properly. Currently, the following tasks are supported:

- `bind_mount_backup`
  - config parameters: 
    - `bind_mounts`: List of bind mounts to backup
- `volume_backup`
  - config parameters: 
    - `volumes`: List of volumes to backup
- `mysql_backup`:
  - config parameters:
    - `database`: Database name
    - `user`: User to use for mysqldump. This should be `root`
    - `password`: Password to use for mysqldump

A separate directory is created for each service and for each backup task registered for that service. Each backup item (such as volumes or bind mounts) also get a separate directory, such that backups of the same item taken at different points in time are gathered in one folder. Example:

```
backup-directory
    |-my-service
    |   |-volume_backup
    |   |   |   |-my-volume
    |   |   |   |   |-2022-01-01-my-volume.tar.gz
    |   |   |   |   |-2022-02-01-my-volume.tar.gz
```

The system is paused during the time of the backup to avoid data inconsistencies.

### CLI Parameters

```shell
backupbot -h
usage: backupbot [-h] [-r ROOT] {docker-compose} destination backup_config

positional arguments:
  {docker-compose}      Specifies the backup adapter to use.
  destination           Absolute path to backup destination root directory.
  backup_config         Path to the backup scheme configuration file (.json).

options:
  -h, --help            show this help message and exit
  -r ROOT, --root ROOT  Path to service root directory.
```

### Manually Starting a Docker Service Using Backed Up Volumes/Bind-Mounts
To (re-)start a container with a bind-mound-backup:

1. Copy the backup file (e.g. `TIMESTAMP-bind_mount.tar.gz`) to the docker-compose service root directory
2. Unpack the tarball somewhere outside `backupbot`'s backup workspace:
   ```
   tar -xzvf TIMESTAMP-bind_mount.tar.gz
   ```
3. Note that the tarball contains the absolute path to the backed up bind mount. Thus, you have to move the bind-mount directory to the `docker-compose`-service root.

To (re-)start a container with a volume backup:

1. Create a new external volume: 
   ```
   docker volume create my-new-volume
   ```
2. Run a new Ubuntu container which bind-mounts the volume tar-file and which mounts the newly created volume `my-new-volume`. The mount point has to match the previous mount point: 
   ```
   docker run --rm --mount source=/absolute/path/to/TIMESTAMP-volume.tar.gz,type=bind,target=/volume-backup.tar.gz --mount source=my-new-volume,type:volume,target:/path/to/mount/point ubuntu:latest sh -c "tar -xzvf volume-backup.tar.gz"
   ```
3. Replace the old volume name (that contains e.g. corrupted data) in the `docker-compose.yaml` by the newly created volume name `my-new-volume`

-------------------------------


## Installation

```shell
pip install -e /path/to/backupbot
```

If you want to install development dependencies alongside `backupbot`, run

```shell
pip install -e /path/to/backupbot[dev]

```

You need docker and docker-compose on your system.
