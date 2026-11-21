/* Identidade casual por papel. Farmer e Citizen são duas pessoas no mesmo browser. */
window.CityFarmPlayer = {
    prefix: function () {
        var role = window.location.pathname.indexOf('/citizen') === 0 ?
            'citizen' : 'farmer';
        return 'cityfarm.' + role + '.player.';
    },
    load: function () {
        var prefix = this.prefix();
        var farmer = prefix === 'cityfarm.farmer.player.';
        return {
            id: localStorage.getItem(prefix + 'id') ||
                (farmer ? localStorage.getItem('cityfarm.player.id') : '') || '',
            name: localStorage.getItem(prefix + 'name') ||
                (farmer ? localStorage.getItem('cityfarm.player.name') : '') || ''
        };
    },
    save: function (name) {
        name = (name || '').trim();
        if (!name || name.length > 24 || !/^[\p{L}\p{N} _-]+$/u.test(name)) {
            throw new Error('Use a nickname with 1–24 letters or numbers.');
        }
        var prefix = this.prefix();
        var id = localStorage.getItem(prefix + 'id') ||
            (prefix === 'cityfarm.farmer.player.' ?
                localStorage.getItem('cityfarm.player.id') : '') || '';
        if (!/^[0-9a-f]{32}$/.test(id)) {
            var bytes = new Uint8Array(16);
            if (window.crypto && window.crypto.getRandomValues) {
                window.crypto.getRandomValues(bytes);
            } else {
                for (var i = 0; i < bytes.length; i++) {
                    bytes[i] = Math.floor(Math.random() * 256);
                }
            }
            id = Array.from(bytes).map(function (b) {
                return b.toString(16).padStart(2, '0');
            }).join('');
        }
        localStorage.setItem(prefix + 'id', id);
        localStorage.setItem(prefix + 'name', name);
        return {id: id, name: name};
    },
    websocketUrl: function () {
        return (window.location.protocol === 'https:' ? 'wss://' : 'ws://') +
            window.location.hostname + ':8888/publihser';
    }
};
