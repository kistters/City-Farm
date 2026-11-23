// Prova que Farmer e Citizen podem negociar em duas abas do mesmo navegador.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const source = fs.readFileSync(
    path.join(__dirname, '../CityFarm/front/js/player.js'), 'utf8');
const stored = new Map();
let seed = 0;
const window = {
    location: {pathname: '/farmer', hostname: 'example.test'},
    crypto: {
        getRandomValues: (bytes) => {
            for (let i = 0; i < bytes.length; i++) bytes[i] = (seed++ % 256);
            return bytes;
        }
    }
};
const localStorage = {
    getItem: (key) => stored.has(key) ? stored.get(key) : null,
    setItem: (key, value) => stored.set(key, value)
};
const context = {window, localStorage, Uint8Array, Array, Math};
vm.runInNewContext(source, context);
const player = context.window.CityFarmPlayer;

assert.equal(player.websocketUrl(), 'ws://example.test:8888/player');
const farmer = player.save('Farmer');
assert.equal(player.load().id, farmer.id);
window.location.pathname = '/citizen';
const citizen = player.save('Citizen');
assert.notEqual(farmer.id, citizen.id);
assert.equal(player.load().id, citizen.id);
window.location.pathname = '/farmer';
assert.equal(player.load().id, farmer.id);
assert.equal(player.load().name, 'Farmer');
window.location.pathname = '/citizen';
assert.equal(player.load().name, 'Citizen');
console.log('Farmer and Citizen keep independent identities.');
