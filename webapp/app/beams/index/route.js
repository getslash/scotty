import Ember from 'ember';

export default Ember.Route.extend({
  afterModel: function(beams, transition) {
    if (beams.length > 0) {
      const self = this;
      // We need the transition to cpmlete before using replace this
      // so that the correct query parameters will be set on the controller
      transition.then(function() {
        self.replaceWith("beams.beam", beams.get("firstObject.id"));
      });
    }
  }
});
