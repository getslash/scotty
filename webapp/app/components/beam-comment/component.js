import Ember from 'ember';

export default Ember.Component.extend({
  editing_comment: false,

  actions: {
    toggle_editing: function() {
      const editing_comment = this.get("editing_comment");
      if (editing_comment) {
        this.get("beam").save();
      }
      this.set("editing_comment", !editing_comment);
    }
  }
});
