import Ember from 'ember';

export default Ember.Component.extend({
  actions: {
    pin: function(pinned) {
      this.get("beam").send("pin", pinned);
    }
  }
});
