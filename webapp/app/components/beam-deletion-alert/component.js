import Component from '@ember/component';
import { computed } from '@ember/object';

export default Component.extend({
  purgeString: computed("purgeTime", function() {
    var purgeTime = this.get("purgeTime");

    if (purgeTime === 0) {
      return "today";
    } else if (purgeTime === 1) {
      return "tomorrow";
    } else {
      return "in " + purgeTime + " days";
    }
  })
});
