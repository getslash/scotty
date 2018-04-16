import Controller from '@ember/controller';
import { computed } from '@ember/object';

export default Controller.extend({
  spacePercent: computed("model.{total_space, used_space}", function() {
    return Math.round(this.get("model.used_space") / this.get("model.total_space") * 100);
  })
});
