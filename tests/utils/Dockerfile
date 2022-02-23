version: '3'

services:
    first_service:
        container_name: service1
        ports:
            - 80:80
            - 443:443
        volumes:
            # this is a comment
            - ./bind_mount1:/container/path
            - named_volume1:/another/container/path
    
    second_service:
        image: source/image
        volumes:
            - named_volume2:/container/path # with a comment
            - ./bind_mount2:/another/container/path

networks:
    - a_random_network