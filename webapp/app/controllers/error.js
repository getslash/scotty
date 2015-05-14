import Ember from 'ember';

export default Ember.Controller.extend({
  error_string: function() {
    var error = this.get("model");
    if (error.status === 404) {
      return "The requested resource could not be found";
    } else {
      return "Something bad happened. Please try to refresh the application";
    }
  }.property("model")
});
