import Component from '@ember/component';
import { task, timeout } from 'ember-concurrency';

const DEBOUNCE_MS = 250;

export default Component.extend({
  keyUp: task(function * () {
    yield timeout(DEBOUNCE_MS);
    this.onChange(this.textbox);
  }).restartable(),

  actions: {
    clean: function() {
      this.set("textbox", "");
      this.onChange("");
    },
  }
});
