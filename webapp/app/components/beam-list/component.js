import Component from '@ember/component';

export default Component.extend({
  actions: {
    beamClick: function(beamId) {
      this.onSelection(beamId);
    }
  }
});
