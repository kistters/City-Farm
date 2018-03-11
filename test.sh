#!/bin/bash

docker build -t pythonrabbitmq_test:latest .


# cd code && bash ../execPython.sh course/strings.py
# Magento
container='pythonrabbitmq_sever_user_1'
host='sever-user.it'

docker run --rm -it --network=$(docker inspect --format='{{.HostConfig.NetworkMode}}' $container) \
--add-host $host:$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $container) \
-v $(pwd)/code:/code pythonrabbitmq_test sh