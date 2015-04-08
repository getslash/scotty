import Ember from 'ember';

export default Ember.Controller.extend({
  reloadModel: function() {
    this.get("model").reload();
  }.observes("model")
});
