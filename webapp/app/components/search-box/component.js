import Ember from 'ember';
import { task, timeout } from 'ember-concurrency';

const DEBOUNCE_MS = 250;

export default Ember.Component.extend({
  keyUp: task(function * () {
    yield timeout(DEBOUNCE_MS);
    this.get("onChange")(this.get("textbox"));
  }).restartable(),

  actions: {
    clean: function() {
      this.set("textbox", "");
      this.get("onChange")("");
    },
  }
});
