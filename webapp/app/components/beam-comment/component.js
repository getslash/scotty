import Component from '@ember/component';

export default Component.extend({
  editing: false,

  actions: {
    toggle: function() {
      const editing = this.editing;
      if (editing) {
        this.beam.save();
      }
      this.set("editing", !editing);
    }
  }
});
