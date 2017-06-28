import Ember from 'ember';
import { task, timeout } from 'ember-concurrency';

export default Ember.Route.extend({
  queryParams: {
    tag: {refreshModel: true},
    email: {refreshModel: true},
    uid: {refreshModel: true}
  },

  periodicRefresh: task(function * () {
    for (;;) {
      yield timeout(1000 * 60 * 5);
      this.refresh();
    }
  }).on("activate").cancelOn('deactivate').drop(),

  model: function(params) {
    if (params.tag) {
      return this.store.query("beam", {tag: params.tag});
    } else if (params.email) {
      return this.store.query("beam", {email: params.email});
    } else if (params.uid) {
      return this.store.query("beam", {uid: params.uid});
    } else {
      return this.store.findAll('beam', {reload: true});
    }
  },

  actions: {
    beamSelected: function(beam) {
      this.controllerFor("beams").set("selectedId", beam);
    }
  }
});
