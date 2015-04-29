#!/bin/bash

CLUSTER_WITH=""
CLUSTERED=""
RAM_NODE=""

while getopts ":m:c:r:" option; do
  case "$option" in
    m)
      CLUSTER_WITH=${OPTARG} ;;
    c)
      CLUSTERED=1 ;;
    r)
      RAM_NODE=1 ;;
    \?)
      echo "
Usage: [options]
  Options:

   -m        master node IP
   -c        clustered
   -r        type node, if it specify that RAM mode
   " >&2
      exit 1
      ;;
  esac
done

if [ -z "$CLUSTERED" ]; then
        # if not clustered then start it normally as if it is a single server
        #service rabbitmq-server start
        /usr/sbin/rabbitmq-server
else
        if [ -z "$CLUSTER_WITH" ]; then
                # If clustered, but cluster with is not specified then again start normally, 
                # could be the first server in the
                # cluster
                /usr/sbin/rabbitmq-server
        else
                /etc/init.d/rabbitmq-server start
                rabbitmqctl stop_app
                if [ -z "$RAM_NODE" ]; then
                        rabbitmqctl join_cluster rabbit@$CLUSTER_WITH
                else
                        rabbitmqctl join_cluster --ram rabbit@$CLUSTER_WITH
                fi
                
                rabbitmqctl start_app
                rabbitmqctl set_policy ha-all "" '{"ha-mode":"all","ha-sync-mode":"automatic"}'
                
                # Tail to keep the a foreground process active..
                tail -f /var/log/rabbitmq/rabbit\@$HOSTNAME.log
        fi
fi

