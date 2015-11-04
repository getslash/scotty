import Ember from 'ember';

export default Ember.Controller.extend({
  space_percent: function() {
    return Math.round(this.get("model.used_space") / this.get("model.total_space") * 100);
  }.property("model.total_space", "model.used_space")
});
