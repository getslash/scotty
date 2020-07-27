import Component from '@ember/component';
import $ from 'jquery';
import { observer } from '@ember/object';
import { task } from 'ember-concurrency';

export default Component.extend({
  pinned: false,

  pin: task(function * (pinned) {
    yield $.ajax({
      type: "put",
      url: "/pin",
      contentType: 'application/json',
      data: JSON.stringify({
        beam_id: parseInt(this.get("beam.id")),
        should_pin: !pinned
      })
    });
    this.onChange();
  }).restartable(),

  didInsertElement() {
    this.updatePinned.perform();
  },

  monitorPins: observer("beam.pins", "beam.pins.length", "session.data.authenticated.id", function() {
    this.updatePinned.perform();
  }),

  updatePinned: task(function * () {
    const store = this.store;

    if (this.get("session.data.authenticated.id") === undefined) {
      this.set("pinned", false);
    } else {
      const me = yield store.find("user", this.get("session.data.authenticated.id"));
      this.set("pinned", this.get("beam.pins").includes(me));
    }
  }).drop()
});
