import Component from '@ember/component';

export default Component.extend({
  editing: false,

  actions: {
    toggle: function() {
      const editing = this.get("editing");
      if (editing) {
        this.get("beam").save();
      }
      this.set("editing", !editing);
    }
  }
});
