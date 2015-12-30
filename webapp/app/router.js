import Ember from 'ember';
import config from './config/environment';

const Router = Ember.Router.extend({
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
  this.route('summary', function() {});
  this.route('tag', {
    path: '/tag/:tag'
  });
  this.route('not-found', {
    path: "*path"
  });
  this.route('pinned');

  this.route('beams', function() {
    this.route('by-user', { path: '/by_user/:uid' });
    this.route('by-email', { path: '/by_email/:email' });
  });
  this.route('filtered-beams');
});

export default Router;
