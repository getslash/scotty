import Component from '@ember/component';
import { computed } from '@ember/object';

export default Component.extend({
  class: "",

  src: computed("beam.{completed,errorMessage}", function() {
    return (this.get("beam.completed") ? (this.get("beam.errorMessage") != null ? "assets/img/folder-error.gif" : "assets/img/folder-regular.gif") : "assets/img/folder-beaming.gif");
  })
});
