import Ember from 'ember';

export default Ember.Route.extend({
  model: function(params) {
      window.history.replaceState( {}, 'beams', '/#/beams?tag=' + params.tag);
  }
});
