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

  getBeams: function(params) {
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

  model: function(params) {
    return this.getBeams(params).then(function(data) {
      return data.filterBy("deleted", false);
    });
  },

  actions: {
    beamSelected: function(beam) {
      this.controllerFor("beams").set("selectedId", beam);
    }
  }
});
