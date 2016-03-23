import Ember from 'ember';
import Materialize from '../mixins/materialize';
import { task, timeout } from 'ember-concurrency';

export default Ember.Route.extend(Materialize, {
  actions: {
    scottyButton: function() {
      this.get("update").perform();
      return false;
    }
  },

  update: task(function * () {
    yield this.store.findAll("beam", {reload: true});
    Ember.run.scheduleOnce('afterRender', function() {
      Ember.$('.tooltipped').tooltip({
        delay: 50
      });
    });
  }).drop(),

  refresh: task(function * () {
    for (;;) {
      yield this.get("update").perform();
      yield timeout(1000 * 5 * 60);
    }
  }).on("activate").cancelOn('deactivate').drop(),

  model: function() {
    var self = this;
    return this.store.findAll('beam').then(function() {
      return self.store.filter('beam', function(beam) {
        return !beam.get("deleted");
      });
    });
  }
});
