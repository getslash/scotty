import Ember from 'ember';

export default Ember.Controller.extend({
  sortKeys: ['start:desc'],
  sortedModel: Ember.computed.sort('model', 'sortKeys'),
  selected_id: null,

  actions: {
    beam_selection: function(beam_id) {
      this.transitionToRoute("beams.beam", beam_id);
    }
  }
});
