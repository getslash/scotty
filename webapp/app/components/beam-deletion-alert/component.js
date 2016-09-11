import Ember from 'ember';

export default Ember.Component.extend({
  purge_str: function() {
    var purge_time = this.get("purge_time");

    if (purge_time === 0) {
      return "today";
    } else if (purge_time === 1) {
      return "tomorrow";
    } else {
      return "in " + purge_time + " days";
    }
  }.property("purge_time").readOnly()
});
