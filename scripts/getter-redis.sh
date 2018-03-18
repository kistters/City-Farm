#!/bin/bash


consultRedis() {
		MILHO=$(echo GET corn | redis-cli)
		TRIGO=$(echo GET wheat | redis-cli)
sleep 0.3
clear; 

cat << EOF
+-----+------+
|plant|  qty |
+-----+------+
|milho| $MILHO      
|trigo| $TRIGO      
+-----+------+
EOF

}

while true; do consultRedis; sleep 0.5; done