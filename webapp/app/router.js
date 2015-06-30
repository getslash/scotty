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
  this.resource('changelog', function() {});
  this.resource('api', function() {});
  this.resource('about', function() {});
  this.resource('summary', function() {});
  this.resource('tag', { path: '/tag/:tag'});
  this.route('not-found', { path: "*path"});
  this.resource('faq', function() {});
  this.route('tags');
});

export default Router;
