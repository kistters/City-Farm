// Citizen: keep this compatible with the Vue 2.1.x used by the game.
var citizen = new Vue({
    el: '#citizen',
    data: {
        status: 'connecting',
        statusClass: {'label label-warning': true},
        tries: null,
        groceries: [],
        productCatalog: [],
        dishes: [],
        dishMessage: '',
        ws_publish: null
    },

    created: function () {
        this.connect();
    },

    methods: {
        connect: function () {
            var self = this;
            var host = window.location.hostname;
            var socket = new WebSocket('ws://' + host + ':8888/publihser');
            self.ws_publish = socket;

            socket.onopen = function () {
                self.status = 'ready';
                self.statusClass = {'label label-success': true};
            };

            socket.onmessage = function (event) {
                var data;
                try {
                    data = JSON.parse(event.data);
                } catch (error) {
                    self.dishMessage = 'Invalid response from the server';
                    return;
                }
                self.handleUpdate(data);
            };

            socket.onerror = function () {
                self.status = 'error';
                self.statusClass = {'label label-danger': true};
            };

            socket.onclose = function () {
                self.status = 'closed';
                self.statusClass = {'label label-danger': true};
                // Reconnect without touching the other Vue components.
                setTimeout(function () {
                    if (self.ws_publish === socket) {
                        self.connect();
                    }
                }, 5000);
            };
        },

        handleUpdate: function (data) {
            if (data.product_catalog) {
                this.productCatalog = data.product_catalog;
            }
            if (data.dishes) {
                this.dishes = data.dishes;
            }
            if (data.groceries) {
                this.groceries = data.groceries;
            }
            if (data.work) {
                this.tries = data.work;
            }
            if (data.dish_ordered) {
                var order = data.dish_ordered;
                this.dishMessage = order.status === 'prepared'
                    ? 'Dish prepared: ' + order.dish
                    : 'Dish ordered: ' + order.dish + '. Waiting for ingredients.';
            }
            if (data.dish_error) {
                this.dishMessage = data.dish_error;
            }
            if (data.eat_ordered) {
                this.dishMessage = data.eat_ordered.status === 'prepared'
                    ? 'Ingredient consumed: ' + data.eat_ordered.product
                    : 'Waiting for harvest: ' + data.eat_ordered.product;
            }
            if (data.eat_error) {
                this.dishMessage = data.eat_error;
            }
        },

        send: function (data) {
            if (!this.ws_publish || this.ws_publish.readyState !== WebSocket.OPEN) {
                this.dishMessage = 'Waiting for WebSocket connection';
                return;
            }
            this.ws_publish.send(JSON.stringify(data));
        },

        orderDish: function (dishId) {
            this.send({order_dish: dishId});
        },

        consume: function (product) {
            this.send({consume: product});
        }
    }
});
