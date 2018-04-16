import Controller from '@ember/controller';
import { computed } from '@ember/object';

export default Controller.extend({
  tag: null,
  email: null,
  uid: null,
  queryParams: ['tag', 'email', 'uid'],

  sortKeys: ['start:desc'],
  sortedModel: computed.sort('model', 'sortKeys'),
  selectedId: null,

  actions: {
    beamSelection: function(beamId) {
      this.transitionToRoute("beams.beam", beamId);
    }
  }
});
