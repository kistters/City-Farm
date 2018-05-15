var dashboard = new Vue({

    // Elemento que o aplicativo será iniciado
    el: "#dashboard",

    // Propriedades do aplicativo
    data: {
        global_msg: '',
        status: 'close',
        web_status: 'close',
        ws_dashboard: null,
        groceries: [],
        userIpList: [],
        ipClick: '',
        statusClass: {'label label-danger': true },
        webStatusClass: {
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
            
            self.ws_dashboard = new WebSocket('ws://'+host+':8888'+'/dashboard');

            self.ws_dashboard.onopen = function() {
                self.web_status = 'open'
                self.webStatusClass = {
                    'label label-success': true
                }

                if (onOpen) {
                    onOpen();
                }
            };

            self.ws_dashboard.onerror = function() {
                self.status = 'fail'
                self.statusClass = {
                    'label label-danger': true
                }
            };

            self.ws_dashboard.onmessage = function(e) {
                self.status = 'recieved'
                self.statusClass = {
                    'label label-info': true
                }

                self.handleUpdate(JSON.parse(e.data));

                setTimeout(() => {
                    self.status = 'waiting'
                    self.statusClass = {
                        'label label-warning': true
                    }
                }, 1000)
            };

            self.ws_dashboard.onclose = function(){
                self.web_status = 'closed'
                self.webStatusClass = {
                    'label label-danger': true
                }

                setTimeout(() => {
                    self.connect();
                }, 5000);
            };
        },

        publish: function(json_data) {

            var self = this;

            if (self.ws_dashboard.readyState !== self.ws_dashboard.OPEN) {

                self.connect(function() {
                    self.publish(JSON.stringify({update:true}));
                });

                return;
            }

            self.ws_dashboard.send(json_data);
        },

        handleUpdate: function(data) {
            if (data.userIpList) {
                this.userIpList = data.userIpList
            }

            if (data.groceries) {
                this.groceries = data.groceries
            }

            if (data.global_msg) {
                this.global_msg = data.global_msg
            }

            if (data.ipClick) {
                this.ipClick = data.ipClick
            }
        }
    }

});