import Ember from 'ember';
import Resolver from 'ember/resolver';
import loadInitializers from 'ember/load-initializers';
import config from './config/environment';

Ember.MODEL_FACTORY_INJECTIONS = true;

var App = Ember.Application.extend({
  modulePrefix: config.modulePrefix,
  podModulePrefix: config.podModulePrefix,
  Resolver: Resolver
});

App.Pollster = Ember.Object.extend({
  interval: function() {
    return 5000; // Time between polls (in ms)
  }.property().readOnly(),

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

  onPoll: function(){
    // Issue JSON request and add data to the store
  }
});

loadInitializers(App, config.modulePrefix);
config.torii.providers['google-oauth2'].redirectUri = window.location.origin;
export default App;

