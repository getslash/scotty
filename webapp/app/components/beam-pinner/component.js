import Ember from 'ember';
import { task } from 'ember-concurrency';

export default Ember.Component.extend({
  pinned: false,

  pin: task(function * (pinned) {
    yield Ember.$.ajax({
      type: "put",
      url: "/pin",
      contentType: 'application/json',
      data: JSON.stringify({
        beam_id: parseInt(this.get("beam.id")),
        should_pin: !pinned
      })
    });
    this.sendAction("refresh_beam");
  }).restartable(),

  monitor_pins: function() {
    this.get("update_pinned").perform();
  }.observes("beam.pins", "session.data.authenticated.id").on("init"),

  update_pinned: task(function * () {
    const store = this.get("store");

    if (this.get("session.data.authenticated.id") === undefined) {
      this.set("pinned", false);
    } else {
      const me = yield store.find("user", this.get("session.data.authenticated.id"));
      this.set("pinned", this.get("beam.pins").contains(me));
    }
  }).drop()
});
