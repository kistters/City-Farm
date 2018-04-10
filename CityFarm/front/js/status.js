var status = new Vue({

    // Elemento que o aplicativo será iniciado
    el: "#status",

    // Propriedades do aplicativo
    data: {
        message: '',
        status: 'close',
        ws_status: null,
        groceries: [],
        ipList: [],
        statusClass: {
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
            self.ws_status = new WebSocket('ws://'+host+':8888'+'/status');

            // Evento que será chamado ao abrir conexão
            self.ws_status.onopen = function() {

                self.status = 'open'
                self.statusClass = {
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

                self.addMessage(JSON.parse(e.data));

                setTimeout(() => {
                    self.status = 'open'
                    self.statusClass = {
                        'label label-success': true
                    }
                }, 1000)
            };

            self.ws_status.onclose = function(){
                self.status = 'closed'
                self.statusClass = {
                    'label label-important': true
                }

                setTimeout(() => {
                    self.connect();
                }, 5000);
            };

        },

        // Método responsável por adicionar uma mensagem de usuário
        addMessage: function(data) {
            if (data.listUser) {
                this.ipList = data.listUser
                return
            }
            if (data.groceries) {
                this.groceries = data.groceries
                return
            }
            this.message = data.message
        }
    }

});