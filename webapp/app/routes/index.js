import Ember from 'ember';
import Materialize from '../mixins/materialize';
import App from '../app';

export default Ember.Route.extend(Materialize, {
  actions: {
    scottyButton: function() {
      this.update();
      return false;
    }
  },

  model: function() {
    var self = this;
    return this.store.findAll('beam').then(function() {
      return self.store.filter('beam', function(beam) {
        return !beam.get("deleted");
      });
    });
  },

  update: function() {
    this.store.findAll("beam", {reload: true}).then(function() {
      Ember.run.scheduleOnce('afterRender', function() {
        Ember.$('.tooltipped').tooltip({
          delay: 50
        });
      });
    });
  },

  afterModel: function() {
    this._super();
    var self = this;

    if (Ember.isNone(this.get('pollster'))) {
      this.set('pollster', App.Pollster.create({
        onPoll: function() {
          self.update();
          return true;
        }
      }));
      this.get('pollster').start();
      this.get('pollster').set("interval", 1000 * 60 * 5);
    }
  }
});
