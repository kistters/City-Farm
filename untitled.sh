#!/bin/bash

##
#
#	''' call docker-compose '''
#   docker-compose run --rm -v $(pwd)/Celery/code:/code celery sh
#
#	''' start all workers '''
#    docker-compose run --rm worker celery -A tasks worker --loglevel=info -Q trigo.comer,milho.comer,trigo.plantar,milho.plantar
#
## 

# progress bar function
prog() {
    local w=10 p=$1;  shift
    # create a string of spaces, then change them to dots
    printf -v dots "%*s" "$(( $p*$w/100 ))" ""; dots=${dots// /.};
    # print those dots on a fixed-width space plus the percentage etc. 
    printf "\r\e[K%-*s %3d %% %s" "$w" "$dots" "$p" "$*"; 
}

ex-next() {
	for x in {1..100} ; do
		if [[ "$x" -gt 0  ]]; then prog "$x" "preparing..."; fi;
		if [[ "$x" -gt 10 ]]; then prog "$x" "waiting..."; fi;
		if [[ "$x" -gt 30 ]]; then prog "$x" "preparing..."; fi;
		if [[ "$x" -gt 40 ]]; then prog "$x" "waiting..."; fi;
		if [[ "$x" -gt 70 ]]; then prog "$x" "starting..."; fi;
		if [[ "$x" -gt 80 ]]; then prog "$x" "going to next..."; fi;
		sleep .03   # do some work here
	done ; echo

	sleep 1
}

docker rm -f $(docker ps -a -q)
#docker-compose build
docker-compose up -d rabbitmq redis

ex-next

gnome-terminal --geometry 80x10+999 -e 'sh -c "docker-compose run --rm worker sh run-worker.sh; echo bye friend; sleep 1;"'

#gnome-terminal --geometry 39x9+-9+-8 -e 'sh -c "docker exec -it db_redis bash /scripts/getter-redis.sh"'

ex-next 

#gnome-terminal --geometry 999x10+999+999 -e 'sh -c "docker stats $(docker ps --format={{.Names}})"'
gnome-terminal --geometry 67x11+-9+262   -e 'sh -c "docker-compose up --remove-orphans websocket"'

ex-next

gnome-terminal --geometry 67x11-7+267   -e 'sh -c "docker-compose up --remove-orphans backend"'
gnome-terminal --geometry 67x11-7+267    -e 'sh -c "docker-compose run --rm backend sh"'

#xwininfo -id $(xprop -root | awk '/_NET_ACTIVE_WINDOW\(WINDOW\)/{print $NF}')