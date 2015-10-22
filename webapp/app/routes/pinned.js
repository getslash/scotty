import Ember from 'ember';

export default Ember.Route.extend({
  model: function() {
    return this.store.find("beam", {
      pinned: true
    });
  },

  renderTemplate: function(controller, model) {
    this.render("index", {
      model: model
    });

    Ember.run.scheduleOnce('afterRender', function() {
      Ember.$('.tooltipped').tooltip({
        delay: 50
      });
    });
  }
});
