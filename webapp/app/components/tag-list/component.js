import Ember from 'ember';

export default Ember.Component.extend({
  actions: {
    modify: function(modifying) {
      this.set('modifying', modifying);
    }
  }
});
