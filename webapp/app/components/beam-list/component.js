import Ember from 'ember';

export default Ember.Component.extend({
  actions: {
    beamClick: function(beamId) {
      this.get("onSelection")(beamId);
    }
  }
});
