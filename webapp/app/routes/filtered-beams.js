import Ember from 'ember';

export default Ember.Route.extend({
  renderTemplate: function(controller, model) {
    if (model.get("length") === 1) {
      this.render("beam", {
        model: model.get("firstObject")
      });
    } else if (model.get("length") === 0) {
      this.render("doesnt-know", { model: this.get("what") });
    } else {
      this.render("index", {
        model: model
      });
    }

    Ember.run.scheduleOnce('afterRender', function() {
      Ember.$('.tooltipped').tooltip({
        delay: 50
      });
    });
  }
});
