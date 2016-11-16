import Ember from 'ember';

export default Ember.Component.extend({
  actions: {
    beam_click: function(beam_id) {
      this.get("beam_selection")(beam_id);
    }
  }
});
