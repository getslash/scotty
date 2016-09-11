import Ember from 'ember';

export default Ember.Route.extend({
  model: function(params) {
    this.transitionTo('beams', {queryParams: {tag: params.tag}});
  }
});
