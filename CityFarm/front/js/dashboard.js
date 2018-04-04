var status = new Vue({

    // Elemento que o aplicativo será iniciado
    el: "#dashboard",

    // Propriedades do aplicativo
    data: {
        message: '',
        groceries: [],
        status: 'close',
        ws_dash: null,
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
            self.ws_dash = new WebSocket('ws://'+host+':8888'+'/dashboard');

            // Evento que será chamado ao abrir conexão
            self.ws_dash.onopen = function() {

                self.status = 'open'
                self.statusClass = {
                    'label label-success': true
                }
                // Se houver método de retorno
                if (onOpen) {
                    onOpen();
                }

                self.sendMessage();
            };

            // Evento que será chamado quando houver erro na conexão
            self.ws_dash.onerror = function() {
                self.status = 'fail'
                self.statusClass = {
                    'label label-important': true
                }
            };

            // Evento que será chamado quando recebido dados do servidor
            self.ws_dash.onmessage = function(e) {
                self.status = 'produce'
                self.statusClass = {
                    'label label-info': true
                }

                self.addMessage(JSON.parse(e.data));

                setTimeout(() => {
                    self.status = 'waiting'
                    self.statusClass = {
                        'label label-warning': true
                    }
                }, 1000)
            };

            self.ws_dash.onclose = function(){
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
            this.groceries = data
        },

        // Método responsável por enviar uma mensagem
        sendMessage: function() {

            var self = this;

            // Se a conexão não estiver aberta
            if (self.ws_dash.readyState !== self.ws_dash.OPEN) {
                // Tentando conectar novamente e caso tenha sucesso
                // envia a mensagem novamente
                self.connect(function() {
                    self.sendMessage();
                });

                // Saindo do método
                return;
            }

            // Envia os dados para o servidor através do websocket
            self.ws_dash.send(JSON.stringify({update: true}));

        },

    }

});