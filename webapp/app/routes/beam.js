import Ember from 'ember';
import Materialize from '../mixins/materialize';

export default Ember.Route.extend(Materialize, {
  model: function(data) {
    return this.store.find('beam', data.beam_id);
  }
});
