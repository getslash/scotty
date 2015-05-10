import Ember from 'ember';

export default Ember.Route.extend({
  model: function(params) {
    return this.store.find("beam", {tag: params.tag });
  },

  renderTemplate: function(controller, model) {
    if (model.get("length") === 1) {
      this.render("beam", {model: model.get("firstObject")});
    } else if (model.get("length") === 0) {
      this.render("doesnt-know");
    } else {
      this.render("index", {model: model});
    }
  }
});
