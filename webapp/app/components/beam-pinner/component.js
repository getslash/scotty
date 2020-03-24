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
    this.get("onChange")();
  }).restartable(),

  didInsertElement() {
    this.updatePinned();
  },

  monitorPins: observer("beam.pins.length", function() {
    this.updatePinned();
  }),

  updatePinned() {
    this.set("pinned", this.get("beam.pins.length") > 0);
  }
});
