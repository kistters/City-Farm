#!/bin/bash


consultRedis() {
		MILHO=$(echo GET milho | redis-cli)
		TRIGO=$(echo GET trigo | redis-cli)
sleep 0.3
clear; 

cat << EOF
+--------+-------------+
| plant  |   qty       |
+------+---------------+
|  milho | $MILHO      |
|  trigo | $TRIGO      |
+--------+-------------+
EOF

}

while true; do consultRedis; sleep 0.5; done