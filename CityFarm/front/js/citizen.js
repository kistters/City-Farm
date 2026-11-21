/* Citizen: aritmética, energia e mercado. Vue 2.1. */
var citizen = new Vue({
    el: '#citizen',
    data: {
        status: 'connecting',
        socket: null,
        playerReady: false,
        playerName: '',
        playerMessage: '',
        productCatalog: [],
        market: {},
        playerState: {coins: 0, energy: 60, plots: []},
        level: 1,
        challenge: null,
        answer: '',
        busy: false,
        gameMessage: ''
    },
    created: function () {
        this.playerName = CityFarmPlayer.load().name;
        this.connect();
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
                if (data.challenge && data.challenge.kind === 'citizen') {
                    self.challenge = data.challenge;
                    self.answer = '';
                    self.busy = false;
                    self.gameMessage = 'Solve the expression to earn coins.';
                }
                if (data.challenge_result && data.challenge_result.kind === 'citizen') {
                    self.challenge = null;
                    self.busy = false;
                    self.answer = '';
                    self.gameMessage = 'Work complete! +' + data.challenge_result.reward.coins + ' coins.';
                }
                if (data.purchase_result) {
                    self.busy = false;
                    self.gameMessage = 'You ate ' + data.purchase_result.product + '! +30 energy, -' +
                        data.purchase_result.price + ' coins.';
                }
                if (data.game_error) {
                    self.busy = false;
                    self.gameMessage = data.game_error;
                }
            };
            socket.onerror = function () { self.status = 'error'; };
            socket.onclose = function () {
                self.status = 'offline';
                self.playerReady = false;
                self.busy = false;
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
                this.playerReady = false;
                this.send({player_register: CityFarmPlayer.save(this.playerName)});
            } catch (error) {
                this.playerMessage = error.message;
            }
        },
        startWork: function () {
            if (!this.playerReady || this.challenge || this.busy || this.playerState.energy < 10) return;
            this.busy = true;
            this.gameMessage = 'Generating arithmetic challenge...';
            if (!this.send({work_start: {level: this.level}})) this.busy = false;
        },
        submitAnswer: function () {
            if (!this.challenge || this.busy) return;
            var input = this.answer.trim();
            if (!/^-?\d+$/.test(input)) {
                this.gameMessage = 'Enter a whole number.';
                return;
            }
            this.busy = true;
            this.gameMessage = 'Checking answer...';
            if (!this.send({challenge_submit: {
                id: this.challenge.id, answer: Number(input)
            }})) this.busy = false;
        },
        buyFood: function (product) {
            if (!this.playerReady || this.busy) return;
            this.busy = true;
            if (!this.send({buy_food: product})) this.busy = false;
        }
    }
});
