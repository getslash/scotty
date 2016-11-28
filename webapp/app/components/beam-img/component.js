import Ember from 'ember';

export default Ember.Component.extend({
  class: "",

  src: function() {
    return (this.get("beam.completed") ? (this.get("beam.error_message") != null ? "/static/assets/img/folder-error.gif" : "/static/assets/img/folder-regular.gif") : "/static/assets/img/folder-beaming.gif");
  }.property("beam.completed", "beam.error_message")
});