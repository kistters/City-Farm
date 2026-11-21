/* Identidade casual compartilhada entre Farmer e Citizen (não é login). */
window.CityFarmPlayer = {
    load: function () {
        return {
            id: localStorage.getItem('cityfarm.player.id') || '',
            name: localStorage.getItem('cityfarm.player.name') || ''
        };
    },
    save: function (name) {
        name = (name || '').trim();
        if (!name || name.length > 24 || !/^[\p{L}\p{N} _-]+$/u.test(name)) {
            throw new Error('Use a nickname with 1–24 letters or numbers.');
        }
        var id = localStorage.getItem('cityfarm.player.id') || '';
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
        localStorage.setItem('cityfarm.player.id', id);
        localStorage.setItem('cityfarm.player.name', name);
        return {id: id, name: name};
    },
    websocketUrl: function () {
        return (window.location.protocol === 'https:' ? 'wss://' : 'ws://') +
            window.location.hostname + ':8888/publihser';
    }
};
