// Regressão: o Vue pode transformar o v-model de type="number" em number.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(
    path.join(__dirname, '../CityFarm/front/js/citizen.js'), 'utf8');
const context = {
    Vue: function (options) { this.methods = options.methods; }
};
vm.runInNewContext(source, context);

function submit(answer) {
    const sent = [];
    const component = {
        challenge: {id: 'challenge-123'},
        busy: false,
        answer,
        gameMessage: '',
        send: (payload) => { sent.push(payload); return true; }
    };
    context.citizen.methods.submitAnswer.call(component);
    return {sent, component};
}

for (const [value, result] of [[47, 47], [0, 0], [-3, -3], [' 42 ', 42]]) {
    const {sent, component} = submit(value);
    assert.equal(sent.length, 1, 'Valid answer must be sent once');
    assert.equal(sent[0].challenge_submit.answer, result);
    assert.equal(component.busy, true);
}
for (const value of ['', null, '1.5', 2.75, 'hello']) {
    const {sent, component} = submit(value);
    assert.equal(sent.length, 0, 'Invalid answer must not be submitted');
    assert.equal(component.gameMessage, 'Enter a whole number.');
    assert.equal(component.busy, false);
}
console.log('Citizen accepts numeric input without trim errors.');
