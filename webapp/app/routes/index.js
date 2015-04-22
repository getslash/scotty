import Ember from 'ember';
import Materialize from '../mixins/materialize';

export default Ember.Route.extend(Materialize, {
  model: function() {
    return this.store.find('beam');
  },

});
