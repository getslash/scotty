import Ember from 'ember';
import App from '../app';
import Materialize from '../mixins/materialize';

export default Ember.Route.extend(Materialize, {
  model: function(data) {
    return this.store.find('beam', data.beam_id);
  },
  deactivate: function() {
    this._super();
    this.get('pollster').stop();
  },
  afterModel: function(model) {
    var self = this;

    if (Ember.isNone(this.get('pollster'))) {
      this.set('pollster', App.Pollster.create({
        onPoll: function() {
          var model = self.get("controller.model");
          if (model.get('completed')) {
            return false;
          } else {
            model.reload();
            return true;
          }
        }
      }));
    }

    if (!model.get('completed')) {
      model.reload();
      this.get('pollster').start();
    }
  }
});
