/* Farmer: somente interface e transporte. Regras no backend. Vue 2.1. */
var farmer = new Vue({
    el: '#farmer',
    data: {
        status: 'connecting',
        socket: null,
        playerReady: false,
        playerName: '',
        playerMessage: '',
        productCatalog: [],
        market: {},
        playerState: {coins: 0, energy: 60, plots: [], plot_upgrade_cost: 20},
        selectedProduct: 'tomato',
        selectedPlot: 0,
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
                if (data.product_catalog) self.productCatalog = data.product_catalog;
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
                    self.showPattern = true;
                    if (self.observationTimer) clearTimeout(self.observationTimer);
                    self.observationTimer = setTimeout(function () {
                        self.showPattern = false;
                    }, data.challenge.observe_seconds * 1000);
                    self.gameMessage = 'Memorize the ingredient positions.';
                }
                if (data.challenge_result && data.challenge_result.kind === 'farmer') {
                    var reward = data.challenge_result.reward;
                    self.challenge = null;
                    self.busy = false;
                    self.showPattern = false;
                    self.gameMessage = 'Harvest complete! +' + reward.qty + ' ' + reward.product;
                }
                if (data.upgrade_result) {
                    self.gameMessage = 'New plot unlocked!';
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
        choosePlot: function (plot) {
            if (!plot.product && !this.challenge) this.selectedPlot = plot.index;
        },
        iconFor: function (name) {
            return name ? '/css/images/' + name + '.svg' : '';
        },
        cycleCell: function (index) {
            if (!this.challenge || this.showPattern || this.busy) return;
            var next = this.answer.slice();
            if (this.challenge.level === 3) {
                var all = [null, 'corn', 'wheat', 'carrot', 'lettuce', 'tomato'];
                next[index] = all[(all.indexOf(next[index]) + 1) % all.length];
            } else {
                next[index] = next[index] ? null : this.challenge.product;
            }
            this.answer = next;
        },
        startFarm: function () {
            if (!this.playerReady || this.challenge || this.busy) return;
            this.busy = true;
            this.gameMessage = 'Generating memory pattern...';
            if (!this.send({farm_start: {
                level: this.level, product: this.selectedProduct,
                plot: this.selectedPlot
            }})) this.busy = false;
        },
        submitAnswer: function () {
            if (!this.challenge || this.showPattern || this.busy) return;
            this.busy = true;
            this.gameMessage = 'Checking pattern...';
            if (!this.send({challenge_submit: {
                id: this.challenge.id, answer: this.answer
            }})) this.busy = false;
        },
        upgrade: function () {
            if (this.busy) return;
            this.busy = true;
            if (!this.send({upgrade_plot: true})) this.busy = false;
        }
    }
});
