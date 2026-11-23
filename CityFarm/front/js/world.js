/* Top-down shared world. Rendering is intentionally framework-free. */
(function () {
    'use strict';

    var TILE = 32;
    var canvas = document.getElementById('world-canvas');
    var ctx = canvas.getContext('2d');
    var joinOverlay = document.getElementById('world-join');
    var joinForm = document.getElementById('join-form');
    var nickname = document.getElementById('player-nickname');
    var joinError = document.getElementById('join-error');
    var online = document.getElementById('online-count');
    var connection = document.getElementById('world-connection');
    var positionLabel = document.getElementById('position-label');
    var enterBuilding = document.getElementById('enter-building');

    var map = [];
    var landmarks = [];
    var players = new Map();
    var mySession = null;
    var socket = null;
    var profile = null;
    var lastMovement = 0;
    var nearby = null;
    ctx.imageSmoothingEnabled = false;

    function rect(color, x, y, w, h) {
        ctx.fillStyle = color;
        ctx.fillRect(Math.round(x), Math.round(y), w, h);
    }

    function drawTile(tile, x, y) {
        var px = x * TILE;
        var py = y * TILE;
        var seed = (x * 37 + y * 19) % 7;
        rect(seed % 2 ? '#81b65d' : '#86bc63', px, py, 32, 32);
        rect('#6da34f', px + (seed * 3) % 22 + 2, py + 5, 3, 2);
        rect('#9ac972', px + (seed * 5) % 20 + 4, py + 24, 3, 3);

        if (tile === 'p') {
            rect('#c0a06c', px, py, 32, 32);
            rect('#d3b782', px + 4, py + 7, 7, 3);
            rect('#ad8c61', px + 22, py + 23, 5, 3);
        } else if (tile === 'f') {
            rect('#8d653c', px, py, 32, 32);
            rect('#6d4d2e', px + 2, py + 3, 28, 5);
            rect('#6d4d2e', px + 2, py + 17, 28, 5);
            rect('#659e41', px + 9, py + 6, 5, 7);
            rect('#8dca54', px + 14, py + 10, 4, 3);
            rect('#659e41', px + 23, py + 18, 5, 7);
        } else if (tile === 'w') {
            rect('#448ea7', px, py, 32, 32);
            rect('#64bac5', px + 2, py + 7, 17, 3);
            rect('#76ccd1', px + 15, py + 22, 14, 3);
        } else if (tile === 't') {
            rect('#577f3e', px + 12, py + 22, 10, 8);
            rect('#2f663b', px + 4, py + 8, 25, 19);
            rect('#367947', px + 8, py + 2, 19, 21);
            rect('#54a060', px + 7, py + 7, 10, 7);
            rect('#6caf67', px + 17, py + 5, 6, 5);
        }
    }

    function drawBuilding(x, y, width, height, roof, label) {
        var px = x * TILE;
        var py = y * TILE;
        var w = width * TILE;
        var h = height * TILE;
        rect('#496544', px + 6, py + h - 3, w - 4, 8);
        rect('#eed7a2', px + 6, py + 30, w - 12, h - 33);
        rect('#3a3e39', px + 1, py + 17, w - 2, 18);
        rect(roof, px, py + 5, w, 26);
        rect('#ffffff30', px + 7, py + 11, w - 14, 3);
        rect('#775433', px + Math.floor(w / 2) - 10, py + h - 28, 20, 28);
        rect('#e1bc75', px + Math.floor(w / 2) + 3, py + h - 16, 3, 3);
        rect('#507c93', px + 13, py + h - 35, 16, 13);
        rect('#507c93', px + w - 28, py + h - 35, 16, 13);
        rect('#e3edd9', px + 2, py + 37, w - 4, 16);
        ctx.font = 'bold 11px monospace';
        ctx.textAlign = 'center';
        ctx.fillStyle = '#294632';
        ctx.fillText(label, px + w / 2, py + 49);
    }

    function drawAvatar(player) {
        var px = Math.round(player.drawX * TILE);
        var py = Math.round(player.drawY * TILE);
        var farmer = player.role === 'farmer';
        var own = player.session === mySession;
        rect('#4b744873', px + 7, py + 27, 20, 5);
        rect('#373e3d', px + 9, py + 23, 6, 6);
        rect('#373e3d', px + 18, py + 23, 6, 6);
        rect(farmer ? '#6d9b50' : '#5176a8', px + 8, py + 12, 17, 13);
        rect('#e1b27d', px + 10, py + 5, 14, 11);
        rect('#4b382d', px + 13, py + 10, 2, 2);
        rect('#4b382d', px + 20, py + 10, 2, 2);
        if (farmer) {
            rect('#76512d', px + 5, py + 5, 24, 5);
            rect('#c79b4d', px + 9, py, 17, 8);
            rect('#926c38', px + 9, py + 6, 17, 2);
        } else {
            rect('#2d5488', px + 7, py + 2, 19, 7);
            rect('#457dc2', px + 8, py, 16, 5);
            rect('#2d5488', px + 21, py + 7, 9, 3);
        }
        if (own) {
            rect('#fff7b3', px + 14, py - 10, 5, 5);
            rect('#fff7b3', px + 12, py - 8, 9, 2);
        }
        ctx.font = 'bold 11px monospace';
        ctx.textAlign = 'center';
        var width = Math.ceil(ctx.measureText(player.name).width) + 12;
        rect('#244332ea', px + 16 - width / 2, py - 25, width, 14);
        ctx.fillStyle = '#fff9dd';
        ctx.fillText(player.name, px + 16, py - 14);
    }

    function render() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        if (!map.length) {
            rect('#85ba61', 0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#254b39';
            ctx.font = 'bold 22px monospace';
            ctx.textAlign = 'center';
            ctx.fillText('Loading the village…', canvas.width / 2, canvas.height / 2);
        } else {
            for (var y = 0; y < map.length; y++) {
                for (var x = 0; x < map[y].length; x++) {
                    drawTile(map[y][x], x, y);
                }
            }
            drawBuilding(4, 2, 3, 3, '#a9503c', 'FARM');
            drawBuilding(20, 2, 3, 3, '#4a6c9e', 'MARKET');
            drawBuilding(24, 11, 2, 2, '#9a7050', 'HOME');
            Array.from(players.values()).sort(function (a, b) {
                return a.y - b.y;
            }).forEach(function (player) {
                player.drawX += (player.x - player.drawX) * 0.28;
                player.drawY += (player.y - player.drawY) * 0.28;
                drawAvatar(player);
            });
        }
        requestAnimationFrame(render);
    }

    function setConnection(message) {
        connection.textContent = message;
    }

    function updateOnline() {
        var count = players.size;
        online.textContent = count + (count === 1 ? ' player online' : ' players online');
    }

    function addPlayer(value) {
        var old = players.get(value.session);
        players.set(value.session, Object.assign({
            drawX: old ? old.drawX : value.x,
            drawY: old ? old.drawY : value.y
        }, value));
        updateOnline();
    }

    function refreshNearby() {
        nearby = null;
        var me = players.get(mySession);
        if (me) {
            nearby = landmarks.find(function (item) {
                return item.role === me.role &&
                    Math.abs(me.x - item.x) + Math.abs(me.y - item.y) <= 2;
            }) || null;
            positionLabel.textContent = me.name + ' · ' +
                (me.role === 'farmer' ? 'Farmer' : 'Citizen');
        } else {
            positionLabel.textContent = 'Choose a character to begin';
        }
        enterBuilding.hidden = !nearby;
        if (nearby) {
            enterBuilding.href = nearby.href;
            enterBuilding.textContent = 'Enter ' + nearby.name + ' (E)';
        }
    }

    function send(payload) {
        if (!socket || socket.readyState !== WebSocket.OPEN) return false;
        socket.send(JSON.stringify(payload));
        return true;
    }

    function join() {
        if (profile) {
            if (!send({world_join: profile})) {
                joinError.textContent = 'Waiting for the connection…';
            } else {
                joinError.textContent = '';
            }
        }
    }

    function connect() {
        var wsUrl = CityFarmPlayer.websocketUrl().replace(/\/player$/, '/world');
        socket = new WebSocket(wsUrl);
        setConnection('Connecting…');
        socket.onopen = function () {
            setConnection('Village online');
            if (profile) join();
        };
        socket.onmessage = function (event) {
            var data;
            try { data = JSON.parse(event.data); }
            catch (error) { setConnection('Invalid server message'); return; }

            if (data.world_map) {
                map = data.world_map.map;
                landmarks = data.world_map.landmarks;
            }
            if (data.world_snapshot) {
                map = data.world_snapshot.map;
                landmarks = data.world_snapshot.landmarks;
                players.clear();
                mySession = data.you;
                data.world_snapshot.players.forEach(addPlayer);
                joinOverlay.hidden = true;
                setConnection('Connected');
                refreshNearby();
            }
            if (data.world_joined) addPlayer(data.world_joined);
            if (data.world_moved) {
                addPlayer(data.world_moved);
                refreshNearby();
            }
            if (data.world_left) {
                players.delete(data.world_left);
                updateOnline();
                refreshNearby();
            }
            if (data.world_error) {
                joinError.textContent = data.world_error;
                setConnection(data.world_error);
            }
        };
        socket.onclose = function () {
            setConnection('Disconnected · reconnecting…');
            players.clear();
            updateOnline();
            mySession = null;
            nearby = null;
            refreshNearby();
            window.setTimeout(function () { connect(); }, 2000);
        };
        socket.onerror = function () { setConnection('Connection failed'); };
    }

    function move(dx, dy) {
        if (!mySession || !socket || socket.readyState !== WebSocket.OPEN) return;
        var now = Date.now();
        if (now - lastMovement < 110) return;
        lastMovement = now;
        send({world_move: {dx: dx, dy: dy}});
    }

    joinForm.addEventListener('submit', function (event) {
        event.preventDefault();
        var role = joinForm.elements.role.value;
        try {
            var saved = CityFarmPlayer.save(nickname.value, role);
            profile = {id: saved.id, name: saved.name, role: role};
            join();
        } catch (error) {
            joinError.textContent = error.message;
        }
    });

    joinForm.querySelectorAll('input[name="role"]').forEach(function (input) {
        input.addEventListener('change', function () {
            if (input.checked) nickname.value = CityFarmPlayer.load(input.value).name;
        });
    });

    document.addEventListener('keydown', function (event) {
        if (event.target.closest('input, textarea, button, select')) return;
        if (event.altKey || event.ctrlKey || event.metaKey) return;
        var key = event.key.toLowerCase();
        var directions = {
            arrowup: [0, -1], w: [0, -1],
            arrowdown: [0, 1], s: [0, 1],
            arrowleft: [-1, 0], a: [-1, 0],
            arrowright: [1, 0], d: [1, 0]
        };
        if (directions[key]) {
            event.preventDefault();
            move(directions[key][0], directions[key][1]);
        } else if (key === 'e' && nearby) {
            window.location.href = nearby.href;
        }
    });

    document.querySelectorAll('[data-move]').forEach(function (button) {
        button.addEventListener('click', function () {
            var direction = button.getAttribute('data-move');
            var options = {up: [0, -1], down: [0, 1],
                left: [-1, 0], right: [1, 0]};
            move(options[direction][0], options[direction][1]);
        });
    });

    nickname.value = CityFarmPlayer.load('farmer').name;
    connect();
    requestAnimationFrame(render);
}());
