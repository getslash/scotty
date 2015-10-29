import Ember from 'ember';
import Resolver from 'ember/resolver';
import loadInitializers from 'ember/load-initializers';
import config from './config/environment';

var App;

Ember.MODEL_FACTORY_INJECTIONS = true;

App = Ember.Application.extend({
  modulePrefix: config.modulePrefix,
  podModulePrefix: config.podModulePrefix,
  Resolver: Resolver
});

App.Pollster = Ember.Object.extend({
  interval: function() {
    return 5000; // Time between polls (in ms)
  }.property(),

  // Schedules the function `f` to be executed every `interval` time.
  schedule: function(f) {
    return Ember.run.later(this, function() {
      if (f.apply(this)) {
        this.set('timer', this.schedule(f));
      }
    }, this.get('interval'));
  },

  // Stops the pollster
  stop: function() {
    Ember.run.cancel(this.get('timer'));
  },

  // Starts the pollster, i.e. executes the `onPoll` function every interval.
  start: function() {
    this.set('timer', this.schedule(this.get('onPoll')));
  },

  onPoll: function() {
    // Issue JSON request and add data to the store
  }
});

App.instanceInitializer({
  name: "relative_time_update",

  initialize: function(instance) {
    let storage = instance.container.lookup("service:store");
    App.update_reltime = App.Pollster.create({
      onPoll: function() {
        let beams = storage.all("beam").content;
        for (var i = 0; i < beams.length; i++) {
          let beam = beams[i].getRecord();
          beam.set("tick", beam.get("tick") + 1);
        }
        return true;
      }
    });
    App.update_reltime.set("interval", 60000);
    App.update_reltime.start();
  }
});

loadInitializers(App, config.modulePrefix);
config.torii.providers['google-oauth2'].redirectUri = window.location.origin;
export default App;
