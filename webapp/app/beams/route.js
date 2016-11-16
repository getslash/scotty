import Ember from 'ember';
import { task, timeout } from 'ember-concurrency';

export default Ember.Route.extend({
  queryParams: {
    tag: {refreshModel: true},
    email: {refreshModel: true},
    uid: {refreshModel: true}
  },

  tag: null,
  email: null,
  actions: {
    scotty_button: function() {
      this.refresh();
      return false;
    },
    beam_selected: function(beam) {
      this.controllerFor("beams").set("selected_id", beam);
    }
  },

  periodic_refresh: task(function * () {
    for (;;) {
      yield timeout(1000 * 60 * 5);
      this.refresh();
    }
  }).on("activate").cancelOn('deactivate').drop(),

  get_beams: function(params) {
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
    return this.get_beams(params).then(function(data) {
      return data.filterBy("deleted", false);
    });
  }
});
