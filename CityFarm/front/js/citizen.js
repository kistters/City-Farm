var citizen = new Vue({

    // Elemento que o aplicativo será iniciado
    el: "#citizen",

    // Propriedades do aplicativo
    data: {
        global_msg: '',
        plant: '',
        tries: null,
        groceries: [],
        productCatalog: [],
        dishes: [],
        dishMessage: '',
        status: 'close',
        ws_publish: null,
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

            self.ws_publish = new WebSocket('ws://'+host+':8888'+'/publihser');

            self.ws_publish.onopen = function() {

                self.status = 'open'
                self.statusClass = {
                    'label label-success': true
                }
                // Se houver método de retorno
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
                self.status = 'consume'
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
            if (data.product_catalog) this.productCatalog = data.product_catalog;
            if (data.dishes) this.dishes = data.dishes;
            if (data.dish_ordered) {
                this.dishMessage = 'Order placed: ' + data.dish_ordered.dish + '. The kitchen will prepare it when all ingredients are available.';
            }
            if (data.dish_error) this.dishMessage = data.dish_error;
            if (data.work) {
                this.tries = data.work

            }
            if (data.groceries) {
                this.groceries = data.groceries
            }
        },

        ingredientList: function (ingredients) {
            return Object.keys(ingredients).map(function(name) {
                return ingredients[name] + '× ' + name.replace(/_/g, ' ');
            }).join(' + ');
        },

        orderDish: function (dish) {
            if (!this.ws_publish || this.ws_publish.readyState !== WebSocket.OPEN) {
                this.dishMessage = 'Wait for WebSocket connection';
                return;
            }
            this.dishMessage = 'Submitting ' + dish + '...';
            this.publish(JSON.stringify({order_dish: dish}));
        },

        consume: function (plant) {
            this.publish(JSON.stringify({consume: plant}));
        },
    }

});