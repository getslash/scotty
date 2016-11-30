import Ember from 'ember';

export default Ember.Component.extend({
  names: [],
  selected: [],

  actions: {
    keyDown(dropdown, e) {
      if (e.keyCode !== 13) { return; }
      let text = e.target.value;
      if (text.length > 0 && this.get('names').indexOf(text) === -1) {
        const selected = this.get("selected");
        selected.pushObject(text);
        this.get("onchange")(selected.toArray());
      }
    },
  }
});
