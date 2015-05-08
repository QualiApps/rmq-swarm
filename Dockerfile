# Version: 0.0.1

FROM fedora:21

MAINTAINER Yury Kavaliou <yury_kavaliou@epam.com>

RUN rpm --import http://www.rabbitmq.com/rabbitmq-signing-key-public.asc
RUN yum install -y https://www.rabbitmq.com/releases/rabbitmq-server/v3.4.3/rabbitmq-server-3.4.3-1.noarch.rpm \
    python-pip \
    && pip install docker-py \
    python-consul \
    httplib2

RUN rabbitmq-plugins enable --offline rabbitmq_mqtt
RUN rabbitmq-plugins enable --offline rabbitmq_management

COPY ./files/startrmq.sh /usr/local/sbin/startrmq.sh
COPY ./files/rabbitmq.config /etc/rabbitmq/rabbitmq.config
COPY ./files/.erlang.cookie /var/lib/rabbitmq/.erlang.cookie
COPY ./files/pre_init.py /usr/local/sbin/pre_init.py
COPY ./files/Docker.py /usr/local/sbin/Docker.py

RUN chown rabbitmq /var/lib/rabbitmq/.erlang.cookie
RUN chmod 700 /usr/local/sbin/startrmq.sh /var/lib/rabbitmq/.erlang.cookie /usr/local/sbin/pre_init.py

ENTRYPOINT ["python", "/usr/local/sbin/pre_init.py"]
CMD [""]

EXPOSE 5672 15672 25672 4369 1883
