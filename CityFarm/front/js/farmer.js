var farmer = new Vue({

    // Elemento que o aplicativo será iniciado
    el: "#farmer",

    // Propriedades do aplicativo
    data: {
        global_msg: '',
        plant: '',
        tries: null,
        groceries: [],
        status: 'close',
        ws_publish: null,
        powWorker: null,
        powBusy: false,
        powMessage: '',
        playerName: '',
        playerId: '',
        playerReady: false,
        playerMessage: '',
        statusClass: {
            'label label-success': false,
            'label label-info': false,
            'label label-danger': true,
            'label label-warning': false
          }
    },

    created: function() {
        this.playerName = localStorage.getItem('cityfarm.player.name') || '';
        this.playerId = localStorage.getItem('cityfarm.player.id') || '';
        // Inicia a conexão com o websocket
        this.connect();
    },

    // Métodos do aplicatvo
    methods: {

        connect: function(onOpen) {

            var self = this;
            var host = window.location.hostname;
            // Conectando
            self.ws_publish = new WebSocket('ws://'+host+':8888'+'/publihser');

            self.ws_publish.onopen = function() {

                self.powBusy = false;
                self.playerReady = false;
                if (self.playerName) self.registerPlayer();
                self.status = 'open'
                self.statusClass = {
                    'label label-success': true
                }

                if (onOpen) {
                    onOpen();
                }
            };

            self.ws_publish.onerror = function() {
                self.status = 'fail'
                self.statusClass = {
                    'label label-danger': true
                }
            };

            self.ws_publish.onmessage = function(e) {
                self.status = 'produce'
                self.statusClass = {
                    'label label-info': true
                }

                self.handleUpdate(JSON.parse(e.data));

                setTimeout(() => {
                    self.status = 'ready'
                    self.statusClass = {
                        'label label-success': true
                    }
                }, 1000)
            };

            self.ws_publish.onclose = function(){
                if (self.powWorker) { self.powWorker.terminate(); self.powWorker = null; }
                self.powBusy = false;
                self.playerReady = false;
                self.status = 'closed'
                self.statusClass = {
                    'label label-danger': true
                }

                setTimeout(() => {
                    self.connect();
                }, 5000);
            };
        },

        publish: function(json_data) {

            var self = this;

            if (self.ws_publish.readyState !== self.ws_publish.OPEN) {
                self.connect(function() {
                    self.publish(JSON.stringify({update:true}));
                });

                return;
            }

            self.ws_publish.send(json_data);
        },

        handleUpdate: function(data) {
            if (data.player_registered) {
                this.playerReady = true;
                this.playerMessage = 'Playing as ' + data.player_registered.name;
            }
            if (data.player_error) {
                this.playerReady = false;
                this.playerMessage = data.player_error;
            }
            if (data.pow_challenge) {
                var worker = new Worker('/js/pow-worker.js');
                this.powWorker = worker;
                var self = this;
                this.powMessage = 'Mining ' + data.pow_challenge.product + ' in browser...';
                worker.onmessage = function(event) {
                    if (event.data.error) {
                        self.powMessage = event.data.error;
                        self.powBusy = false;
                    } else {
                        self.powMessage = 'Found proof after ' + event.data.attempts + ' hashes; submitting...';
                        self.publish(JSON.stringify({pow_submit: {
                            id: event.data.id, nonce: event.data.nonce
                        }}));
                    }
                    worker.terminate();
                    self.powWorker = null;
                };
                worker.onerror = function() {
                    self.powMessage = 'Mining failed';
                    self.powBusy = false;
                    worker.terminate();
                    self.powWorker = null;
                };
                worker.postMessage(data.pow_challenge);
            }
            if (data.pow_status === 'submitted') {
                this.powMessage = 'Proof sent for verification; watch the dashboard.';
                this.powBusy = false;
            }
            if (data.pow_error) {
                this.powMessage = data.pow_error;
                this.powBusy = false;
            }
            if (data.work) {
                this.tries = data.work
            }

            if (data.groceries) {
                this.groceries = data.groceries
            }
        },

        registerPlayer: function () {
            var name = this.playerName.trim();
            if (!name || name.length > 24 || !/^[\\p{L}\\p{N} _-]+$/u.test(name)) {
                this.playerMessage = 'Choose a name (1–24 characters)';
                return;
            }
            if (!this.ws_publish || this.ws_publish.readyState !== WebSocket.OPEN) {
                this.playerMessage = 'Waiting for connection';
                return;
            }
            if (!/^[0-9a-f]{32}$/.test(this.playerId)) {
                var bytes = new Uint8Array(16);
                for (var i = 0; i < bytes.length; i++) {
                    bytes[i] = Math.floor(Math.random() * 256);
                }
                this.playerId = Array.from(bytes).map(function(b) {
                    return b.toString(16).padStart(2, '0');
                }).join('');
            }
            this.playerName = name;
            localStorage.setItem('cityfarm.player.name', name);
            localStorage.setItem('cityfarm.player.id', this.playerId);
            this.playerReady = false;
            this.publish(JSON.stringify({player_register: {
                id: this.playerId, name: name
            }}));
        },

        produce: function (plant) {
            if (!this.playerReady) {
                this.powMessage = 'Register your Farmer name first';
                return;
            }
            if (this.groceries.indexOf(plant) !== -1) {
                if (this.powBusy) return;
                if (!this.ws_publish || this.ws_publish.readyState !== WebSocket.OPEN) {
                    this.powMessage = 'Wait for WebSocket connection';
                    return;
                }
                this.powBusy = true;
                this.powMessage = 'Requesting a ' + plant + ' challenge...';
                this.publish(JSON.stringify({pow_start: plant}));
                return;
            }
            this.publish(JSON.stringify({produce: plant}));
        },
    }

});