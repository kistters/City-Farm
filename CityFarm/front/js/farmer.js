/* Farmer: somente interface e transporte. Regras no backend. Vue 2.1. */
var farmer = new Vue({
    el: '#farmer',
    data: {
        status: 'connecting',
        socket: null,
        playerReady: false,
        playerName: '',
        playerMessage: '',
        market: {},
        playerState: {coins: 0, energy: 60, soil_health: 100},
        soilCosts: {1: 10, 2: 35, 3: 20},
        levelNames: {1: 'Monocultura familiar', 2: 'Monocultura latifúndio', 3: 'Multicultura'},
        level: 1,
        challenge: null,
        showPattern: false,
        answer: [],
        observationTimer: null,
        busy: false,
        gameMessage: ''
    },
    created: function () {
        this.playerName = CityFarmPlayer.load().name;
        this.connect();
    },
    computed: {
        visibleCells: function () {
            if (!this.challenge) return [];
            return this.showPattern ? this.challenge.pattern : this.answer;
        },
        boardSize: function () {
            return this.challenge ? this.challenge.size : 3;
        },
        canPlant: function () {
            return this.playerReady && !this.busy && !this.challenge &&
                this.playerState.soil_health >= this.soilCosts[this.level];
        }
    },
    methods: {
        connect: function () {
            var self = this;
            var socket = new WebSocket(CityFarmPlayer.websocketUrl());
            this.socket = socket;
            socket.onopen = function () {
                self.status = 'ready';
                self.playerReady = false;
                if (self.playerName) self.registerPlayer();
            };
            socket.onmessage = function (event) {
                var data;
                try { data = JSON.parse(event.data); }
                catch (e) { self.gameMessage = 'Invalid server response'; return; }
                if (data.market) self.market = data.market;
                if (data.player_state) self.playerState = data.player_state;
                if (data.player_registered) {
                    self.playerReady = true;
                    self.playerMessage = 'Playing as ' + data.player_registered.name;
                }
                if (data.challenge && data.challenge.kind === 'farmer') {
                    self.challenge = data.challenge;
                    self.busy = false;
                    self.answer = Array(data.challenge.size * data.challenge.size).fill(null);
                    self.beginObservation();
                    self.gameMessage = 'Memorize the ingredient positions.';
                }
                if (data.challenge_cancelled && self.challenge &&
                    data.challenge_cancelled.id === self.challenge.id) {
                    if (self.observationTimer) clearTimeout(self.observationTimer);
                    self.observationTimer = null;
                    self.challenge = null;
                    self.showPattern = false;
                    self.answer = [];
                    self.busy = false;
                    self.gameMessage = 'Desafio cancelado. Nenhum alimento ou ponto de solo foi gasto.';
                }
                if (data.challenge_result && data.challenge_result.kind === 'farmer') {
                    var reward = data.challenge_result.reward;
                    self.challenge = null;
                    self.busy = false;
                    self.showPattern = false;
                    if (self.observationTimer) clearTimeout(self.observationTimer);
                    self.observationTimer = null;
                    self.gameMessage = 'Harvest complete! +' + reward.qty +
                        ' Food · Soil −' + reward.soil_cost;
                }
                if (data.care_result) {
                    self.gameMessage = data.care_result.cost ?
                        'Soil prepared. −' + data.care_result.cost + ' coins.' :
                        'Basic soil care complete.';
                    self.busy = false;
                }
                if (data.game_error) {
                    self.gameMessage = data.game_error;
                    self.busy = false;
                    if (data.game_error.indexOf('expired') !== -1 ||
                        data.game_error.indexOf('already completed') !== -1) {
                        self.challenge = null;
                        if (self.observationTimer) clearTimeout(self.observationTimer);
                        self.showPattern = false;
                    }
                }
            };
            socket.onerror = function () { self.status = 'error'; };
            socket.onclose = function () {
                self.status = 'offline';
                self.playerReady = false;
                self.busy = false;
                if (self.observationTimer) clearTimeout(self.observationTimer);
                self.challenge = null;
                setTimeout(function () {
                    if (self.socket === socket) self.connect();
                }, 2500);
            };
        },
        send: function (payload) {
            if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
                this.gameMessage = 'Waiting for the server';
                this.busy = false;
                return false;
            }
            this.socket.send(JSON.stringify(payload));
            return true;
        },
        registerPlayer: function () {
            try {
                var profile = CityFarmPlayer.save(this.playerName);
                this.playerReady = false;
                this.send({player_register: profile});
            } catch (error) {
                this.playerMessage = error.message;
            }
        },
        cycleCell: function (index) {
            if (!this.challenge || this.showPattern || this.busy) return;
            var next = this.answer.slice();
            if (this.challenge.level === 3) {
                var all = [null, 'corn', 'wheat', 'carrot', 'lettuce', 'tomato'];
                next[index] = all[(all.indexOf(next[index]) + 1) % all.length];
            } else {
                next[index] = next[index] ? null : (this.challenge.symbol || 'food');
            }
            this.answer = next;
        },
        beginObservation: function () {
            if (!this.challenge) return;
            var self = this;
            this.showPattern = true;
            if (this.observationTimer) clearTimeout(this.observationTimer);
            this.observationTimer = setTimeout(function () {
                self.showPattern = false;
                self.observationTimer = null;
            }, this.challenge.observe_seconds * 1000);
        },
        reviewPattern: function () {
            if (!this.challenge || this.busy || this.showPattern) return;
            this.beginObservation();
            this.gameMessage = 'Memorize novamente. Sua resposta foi preservada.';
        },
        cancelChallenge: function () {
            if (!this.challenge || this.busy) return;
            this.busy = true;
            this.gameMessage = 'Cancelando desafio...';
            if (!this.send({farm_cancel: {id: this.challenge.id}})) this.busy = false;
        },
        startFarm: function () {
            if (!this.canPlant) return;
            this.busy = true;
            this.gameMessage = 'Generating memory pattern...';
            if (!this.send({farm_start: {level: this.level}})) this.busy = false;
        },
        submitAnswer: function () {
            if (!this.challenge || this.showPattern || this.busy) return;
            this.busy = true;
            this.gameMessage = 'Checking pattern...';
            if (!this.send({challenge_submit: {
                id: this.challenge.id, answer: this.answer
            }})) this.busy = false;
        },
        careSoil: function () {
            if (!this.playerReady || this.busy || this.playerState.soil_health >= 10) return;
            this.busy = true;
            this.send({care_for_soil: true});
        },
        prepareSoil: function () {
            if (!this.playerReady || this.busy || this.playerState.soil_health >= 100 ||
                this.playerState.coins < 5) return;
            this.busy = true;
            this.send({prepare_soil: true});
        }
    }
});
