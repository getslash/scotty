import Ember from 'ember';
import config from './config/environment';

var Router = Ember.Router.extend({
  location: config.locationType
});

Router.map(function() {
  this.resource('setup', function() {});
  this.resource('login', function() {});
  this.resource('beam', { path: '/beam/:beam_id' });
  this.resource('new-beam', function() {});
});

export default Router;
