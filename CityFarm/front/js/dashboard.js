var status = new Vue({

    // Elemento que o aplicativo será iniciado
    el: "#dashboard",

    // Propriedades do aplicativo
    data: {
        global_msg: '',
        status: 'close',
        web_status: 'close',
        ws_status: null,
        groceries: [],
        userIpList: [],
        statusClass: {'label label-important': true },
        webStatusClass: {
            'label label-success': false,
            'label label-info': false,
            'label label-important': true,
            'label label-warning': false
          }
    },

    created: function() {
        // Inicia a conexão com o websocket
        this.connect();
    },

    // Métodos do aplicatvo
    methods: {

        // Método responsável por iniciar conexão com o websocket
        connect: function(onOpen) {

            var self = this;
            var host = window.location.hostname;
            
            // Conectando
            self.ws_status = new WebSocket('ws://'+host+':8888'+'/dashboard');

            // Evento que será chamado ao abrir conexão
            self.ws_status.onopen = function() {
                self.web_status = 'open'
                self.webStatusClass = {
                    'label label-success': true
                }
                // Se houver método de retorno
                if (onOpen) {
                    onOpen();
                }
            };

            // Evento que será chamado quando houver erro na conexão
            self.ws_status.onerror = function() {
                self.status = 'fail'
                self.statusClass = {
                    'label label-important': true
                }
            };

            // Evento que será chamado quando recebido dados do servidor
            self.ws_status.onmessage = function(e) {
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

            self.ws_status.onclose = function(){
                self.web_status = 'closed'
                self.webStatusClass = {
                    'label label-important': true
                }

                setTimeout(() => {
                    self.connect();
                }, 5000);
            };

        },

        // Método responsável por adicionar uma mensagem de usuário
        handleUpdate: function(data) {
            if (data.userIpList) {
                this.userIpList = data.userIpList
            }

            if (data.groceries) {
                this.groceries = data.groceries
            }

            this.global_msg = data.global_msg
        }
    }

});