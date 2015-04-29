Installation
--------------

1. Install [Docker](https://www.docker.com)

2. Download automated build from public Docker Hub Registry: `docker pull qapps/rabbitmq`
(alternatively, you can build an image from Dockerfile: `docker build -t="qapps/rabbitmq" github.com/qualiapps/rabbitmq`)

Start RabbitMQ broker as a daemon
--------------

`docker run -d -p 25672:25672 -p 4369:4369 -p 15672:15672 -p 1883:1883 -p 5672:5672 -h rabbitmq --name rabbitmq qapps/rabbitmq [options]`


Specify these options, if you want to configure a cluster
-------------

options:

`-m` - master node IP

`-c` - clustered

`-r` - type node, if it's specify that RAM mode
