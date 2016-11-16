import { moduleForComponent, test } from 'ember-qunit';
import hbs from 'htmlbars-inline-precompile';

moduleForComponent('beam-deletion-alert', 'Integration | Component | beam deletion alert', {
  integration: true
});

test('it renders', function(assert) {
  // Set any properties with this.set('myProperty', 'value');
  // Handle any actions with this.on('myAction', function(val) { ... });

  this.render(hbs`{{beam-deletion-alert}}`);

  assert.equal(this.$().text().trim(), '');

  // Template block usage:
  this.render(hbs`
    {{#beam-deletion-alert}}
      template block text
    {{/beam-deletion-alert}}
  `);

  assert.equal(this.$().text().trim(), 'template block text');
});
