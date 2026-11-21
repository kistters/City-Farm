/* Read-only market and activity dashboard; also used in Farmer sidebar. */
var dashboard = new Vue({
    el: '#dashboard',
    data: {
        web_status: 'connecting',
        market: {},
        history: [],
        productCatalog: [],
        ws_dashboard: null
    },
    created: function () {
        this.connect();
    },
    methods: {
        connect: function () {
            var self = this;
            var protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
            var socket = new WebSocket(protocol + window.location.hostname + ':8888/dashboard');
            this.ws_dashboard = socket;
            socket.onopen = function () { self.web_status = 'open'; };
            socket.onmessage = function (event) {
                var data;
                try { data = JSON.parse(event.data); }
                catch (e) { return; }
                if (data.market) self.market = data.market;
                if (data.history) self.history = data.history;
                if (data.product_catalog) self.productCatalog = data.product_catalog;
            };
            socket.onerror = function () { self.web_status = 'error'; };
            socket.onclose = function () {
                self.web_status = 'offline';
                setTimeout(function () {
                    if (self.ws_dashboard === socket) self.connect();
                }, 2500);
            };
        }
    }
});
