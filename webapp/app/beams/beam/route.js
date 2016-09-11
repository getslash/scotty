import Ember from 'ember';
import { task, timeout } from 'ember-concurrency';

export default Ember.Route.extend({
  model: function(data) {
    return Ember.RSVP.hash({
      beam: this.store.find('beam', data.id),
      trackers: this.store.findAll('tracker')
    });
  },


  afterModel: function(model, transision) {
    transision.send("beam_selected", model.beam.id);
    this.get('refresh').perform(model.beam);
  },

  refresh: task(function * (beam) {
    while (!beam.get('completed')) {
      yield beam.reload();
      yield timeout(1000 * 5);
    }
  }).cancelOn('deactivate').drop()
});
