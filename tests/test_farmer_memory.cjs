// Testa revisão do padrão sem limpar a resposta e cancelamento do Farmer.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const code = fs.readFileSync(
    path.join(__dirname, '../CityFarm/front/js/farmer.js'), 'utf8');

const pending = new Map();
let nextTimer = 1;
const context = {
    Vue: function (config) { this.methods = config.methods; },
    setTimeout: (callback, duration) => {
        const id = nextTimer++;
        pending.set(id, {callback, duration});
        return id;
    },
    clearTimeout: (id) => pending.delete(id)
};
vm.runInNewContext(code, context);

const sent = [];
const methods = context.farmer.methods;
const originalAnswer = ['tomato', null, 'carrot'];
const farmer = {
    challenge: {id: 'x'.repeat(32), observe_seconds: 6},
    busy: false,
    showPattern: false,
    answer: originalAnswer,
    observationTimer: null,
    gameMessage: '',
    send: (payload) => { sent.push(payload); return true; }
};
farmer.beginObservation = () => methods.beginObservation.call(farmer);

methods.reviewPattern.call(farmer);
assert.equal(farmer.showPattern, true);
assert.equal(farmer.answer, originalAnswer);
assert.equal(pending.get(farmer.observationTimer).duration, 6000);
pending.get(farmer.observationTimer).callback();
assert.equal(farmer.showPattern, false);
assert.equal(farmer.answer, originalAnswer);

// Quando a referência desaparece, ela pode ser mostrada outra vez.
methods.reviewPattern.call(farmer);
assert.equal(farmer.showPattern, true);
assert.equal(farmer.answer, originalAnswer);

// O cancelamento envia apenas o ID da tentativa atual para o backend.
methods.cancelChallenge.call(farmer);
assert.equal(farmer.busy, true);
assert.equal(sent.length, 1);
assert.equal(sent[0].farm_cancel.id, farmer.challenge.id);
console.log('Farmer review/cancel behaviour: passed.');
