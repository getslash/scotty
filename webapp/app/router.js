import Ember from 'ember';
import config from './config/environment';

var Router = Ember.Router.extend({
  location: config.locationType
});

Router.map(function() {
  this.route('setup', function() {});
  this.route('login', function() {});
  this.route('beam', {
    path: '/beam/:beam_id'
  });
  this.route('new-beam', function() {});
  this.route('changelog', function() {});
  this.route('api', function() {});
  this.route('about', function() {});
  this.route('summary', function() {});
  this.route('tag', {
    path: '/tag/:tag'
  });
  this.route('not-found', {
    path: "*path"
  });
  this.route('faq', function() {});
  this.route('pinned');
});

export default Router;
