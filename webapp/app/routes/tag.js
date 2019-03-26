import Route from '@ember/routing/route';

export default Route.extend({
  model: function(params) {
    this.transitionTo('beams', {
      queryParams: {tag: params.tag}
    });
  }
});
