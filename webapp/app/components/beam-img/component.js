import Ember from 'ember';

export default Ember.Component.extend({
  class: "",

  src: function() {
    return (this.get("beam.completed") ? (this.get("beam.errorMessage") != null ? "assets/img/folder-error.gif" : "assets/img/folder-regular.gif") : "assets/img/folder-beaming.gif");
  }.property("beam.completed", "beam.errorMessage")
});
