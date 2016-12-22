import Ember from 'ember';

export default Ember.Component.extend({
  purgeString: function() {
    var purgeTime = this.get("purgeTime");

    if (purgeTime === 0) {
      return "today";
    } else if (purgeTime === 1) {
      return "tomorrow";
    } else {
      return "in " + purgeTime + " days";
    }
  }.property("purgeTime").readOnly()
});
