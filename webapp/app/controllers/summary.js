import Ember from 'ember';

export default Ember.Controller.extend({
  space_percent: function() {
    return (this.get("model.used_space") / this.get("model.total_space") * 100).toFixed(0);
  }.property("model.total_space", "model.used_space")
});
