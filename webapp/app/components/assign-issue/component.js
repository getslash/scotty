import Ember from 'ember';

export default Ember.Component.extend({
  editing_comment: false,
  dest: null,

  didReceiveAttrs: function() {
    this.set("dest", this.get("trackers.firstObject"));
  },

  actions: {
    toggle_editing: function(submit) {
      const editing_comment = this.get("editing_comment");
      const name = this.get("name");
      if (editing_comment) {
        if (submit && name) {
          this.get("submit")(this.get("dest"), name);
        }
      }
      this.set("editing_comment", !editing_comment);
    },

    change: function(selected) {
      this.set("dest", selected);
    }
  }
});
