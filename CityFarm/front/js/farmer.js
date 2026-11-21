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
        statusClass: {
            'label label-success': false,
            'label label-info': false,
            'label label-danger': true,
            'label label-warning': false
          }
    },

    created: function() {
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
            if (data.pow_challenge) {
                var worker = new Worker('/js/pow-worker.js');
                this.powWorker = worker;
                var self = this;
                this.powMessage = 'Mining tomato in browser...';
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

        produce: function (plant) {
            if (plant === 'tomato') {
                if (this.powBusy) return;
                if (!this.ws_publish || this.ws_publish.readyState !== WebSocket.OPEN) {
                    this.powMessage = 'Wait for WebSocket connection';
                    return;
                }
                this.powBusy = true;
                this.powMessage = 'Requesting a tomato challenge...';
                this.publish(JSON.stringify({pow_start: 'tomato'}));
                return;
            }
            this.publish(JSON.stringify({produce: plant}));
        },
    }

});