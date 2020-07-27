import Component from '@ember/component';

export default Component.extend({
  names: [],
  selected: [],

  actions: {
    keyDown(dropdown, e) {
      if (e.keyCode !== 13) { return; }
      let text = e.target.value;
      if (text.length > 0 && this.names.indexOf(text) === -1) {
        const selected = this.selected;
        selected.pushObject(text);
        this.onchange(selected.toArray());
      }
    },
  }
});
