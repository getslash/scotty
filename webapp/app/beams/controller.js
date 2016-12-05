import Ember from 'ember';

export default Ember.Controller.extend({
  tag: null,
  email: null,
  uid: null,
  queryParams: ['tag', 'email', 'uid'],

  sortKeys: ['start:desc'],
  sortedModel: Ember.computed.sort('model', 'sortKeys'),
  selectedId: null,

  actions: {
    beamSelection: function(beamId) {
      this.transitionToRoute("beams.beam", beamId);
    }
  }
});
