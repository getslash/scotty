import Ember from 'ember';
import Materialize from '../mixins/materialize';
import App from '../app';

export default Ember.Route.extend(Materialize, {
  model: function() {
    return this.store.find('beam');
  },

  afterModel: function() {
    this._super();
    var self = this;

    if (Ember.isNone(this.get('pollster'))) {
      this.set('pollster', App.Pollster.create({
        onPoll: function() {
          self.store.fetchAll("beam");
          return true;
        }
      }));
      this.get('pollster').start();
      this.get('pollster').set("interval", 1000 * 60 * 5);
    }
  }
});
