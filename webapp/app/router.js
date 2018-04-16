import EmberRouter from '@ember/routing/router';
import config from './config/environment';

const Router = EmberRouter.extend({
  location: config.locationType,
  rootURL: config.rootURL
});

Router.map(function() {
  // this.route('index', function() {
  // });
  this.route('setup', function() {});
  this.route('login', function() {});
  this.route('new-beam', function() {});
  this.route('api', function() {});
  this.route('tag', {
    path: '/tag/:tag'
  });
  this.route('not-found', {
    path: "*path"
  });

  this.route('beams', function() {
    this.route('by-user', { path: '/by_user/:uid' });
    this.route('by-email', { path: '/by_email/:email' });
    this.route('beam', { path: '/:id' });
  });
  this.route('filtered-beams');
  this.route('summary');
});

export default Router;
