# Folder structure
- backups/
    - service1
        - bind mounts
            - bind mount 1
            - bind mount 2
        - named volumes
            - named volume 1
            - named volume 2

# Backup Adapter
## Common Tasks
- read config file
    - parse into format:
        ```
        {
            service_name: {
                host_directories: [],
                volumes: []
            }
        }
        ```
        where `host_directories` are absolute paths to directories on the host that are mapped into a container (e.g. Docker bind mounts); `volumes` are persistent volumes provided by the container framework (e.g. Docker named volumes).
            
- host directories:
    - backup host directories
        - tar directory
    - find host directory paths
- volumes:
    - map volumes and containers
    - stop running container
    - backup volume via temporary container
        - tar directory
    - restart stopped container

## Class BackupBot
- use adapter to 
    - collect config files `adapter.collect_config_files()`
    - create dict containing information on host directories and volues `adatper.parse_config()`
    - create target folder structure if necessary `self.create_target_folders()`
    - traverse through mounted host directories and `adapter.backup_host_directory()`
    - traverse through volumes and do backup procedure
    - after each backup: update version numbers `self.update_backup_versions(dir: Path)`

```
def update_backup_versions(dir: Path) -> None:
    for all files:
        - get highest version number (==> oldest backup)
        - sort files from oldest to newest creation date
        - rename files from oldest to newest:
            - cut away version number if it exists
            - append new version number, starting from oldest +1 and decreasing
```



## (Abstract) Class ContainerBackupAdapter
- parse config file
- backup host directory
- stop running container
- tar volume via temporary container
- restart stopped container with mounted volume

# Backing Up Volumes

Use a **backup scheme config file** (JSON), which specifies backup schemes to apply to certain containers. Load config
file at start and execute backup schemes for each container. This makes deciding for which parts of a container to back
up flexible. E.g. back up a MySQL database, but not the volume used by the container to store the database on.


Backup scheme "backup_volumes":

- stop container
- run tar command in temporary container (all specified volumes mounted; bind mount to transfer data to host)
- mount points for volumes on temporary container will be the same as on original container, so the mount points must be
known!
- start container

Backup scheme "backup_mysql":

- mount bind moint
- execute mysqldump on running container
- execute `docker cp` to copy dump file to host (via `container.get_archive()` in python docker framework)
- execute `rm` command on running container to remove dump file

Keys from the docker file can be used as follows: `container_name.hierachy.to.key`, e.g in case of a MySQL container: 
`database_container.environment.MYSQL_USER`.

Necessary **Docker utility functions**:
- `docker_cp_archive(container_name, path/to/file/or/dir, targer_file.tar)` copies a file or directory from docker
container to host
- `stopped_container(container_name)` context manager which stops a running container on entrance and stops it on exit



## Backup scheme config file:
```
{
    container_name: [
        {
            type: "backup_host_directories",
            directories: ["all"],
        },
        {
            type: "backup_volume",
            volumes: [volume1, volume2, ...],
        },
        {
            type: "backup_mysql",
            database: "full.key.to.database.name.in.docker-compose",
            user: "root"/"full.key.to.database.user.in.docker-compose",
            password: "full.key.to.database.password.in.docker-compose",
        }
    ]
}
```

- command can be something like `tar - czf`
- `use_mountpoint` makes it so that the mountpoint is appended to the command string

## Back up volume via tar
https://jareklipski.medium.com/backup-restore-docker-named-volumes-350397b8e362

idea:
- stop and start containers via context manager:
```
with pause_container('container_name') as container:
    <start new container with mounted volume, tar volume content, stop temporary container>
```

- function would look something like this:
```
from contextlib import contextmanager
@contextmanager
def pause_container(container_id: str) -> None:
    stop_container(container_id)
    yield
    start_container(container_id)
```
## Stopping containers
Issue: Some containers need to be runnung during the back up (e.g. MySQL containers). The system should not be making changes during the backup.


- stop container all containers (via docker-compose stop?)
- for those containers that need a temporary container (volumes, mysql): start container from same image and do backup