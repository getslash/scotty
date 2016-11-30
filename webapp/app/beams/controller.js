import Ember from 'ember';

export default Ember.Controller.extend({
  sortKeys: ['start:desc'],
  sortedModel: Ember.computed.sort('model', 'sortKeys'),
  selectedId: null,

  actions: {
    beamSelection: function(beamId) {
      this.transitionToRoute("beams.beam", beamId);
    }
  }
});
