import Ember from 'ember';

export default Ember.Component.extend({
  editing: false,
  dest: null,

  didReceiveAttrs: function() {
    this.set("dest", this.get("trackers.firstObject"));
  },

  actions: {
    toggle: function(submit) {
      const editing = this.get("editing");
      const name = this.get("name");
      if (editing) {
        if (submit && name) {
          this.get("submit")(this.get("dest"), name);
        }
      }
      this.set("editing", !editing);
    },

    change: function(selected) {
      this.set("dest", selected);
    }
  }
});
