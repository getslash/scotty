import Ember from 'ember';
import { task, timeout } from 'ember-concurrency';

export default Ember.Route.extend({
  beam: null,

  model: function(data) {
    const self = this;
    return this.store.find('beam', data.beam_id).then(function(beam) {
      self.get('refresh').perform(beam);
      return beam;
    });
  },

  refresh: task(function * (beam) {
    while (!beam.get('completed')) {
      yield beam.reload();
      yield timeout(1000 * 5);
    }
  }).cancelOn('deactivate').drop()

});
