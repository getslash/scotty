import Ember from 'ember';

export default Ember.Route.extend({
  model: function(data) {
    return this.store.find('beam', data.beam_id);
  }
});
