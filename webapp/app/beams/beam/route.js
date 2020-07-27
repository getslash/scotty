import Route from '@ember/routing/route';
import { hash } from 'rsvp';
import { task, timeout } from 'ember-concurrency';

export default Route.extend({
  model: function(data) {
    return hash({
      beam: this.store.find('beam', data.id),
      trackers: this.store.findAll('tracker')
    });
  },

  afterModel: function(model, transision) {
    transision.send("beamSelected", model.beam.id);
    this.refresh.perform(model.beam);
  },

  refresh: task(function * (beam) {
    while (!beam.get('completed')) {
      yield beam.reload();
      yield timeout(1000 * 5);
    }
  }).cancelOn('deactivate').drop()
});
