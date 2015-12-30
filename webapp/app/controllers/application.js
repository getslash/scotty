import Ember from 'ember';

export default Ember.Controller.extend({
  queryParams: ['view'],
  view: "",
  modal_content: "",
  session: Ember.inject.service('session'),

  iframe: function() {
    return this.get("view") === "iframe";
  }.property("view"),

  actions: {
    login_error: function(error) {
      if (error === 401) {
        this.set('modal_content', 'Scotty must be used with Infinidat accounts');
      } else {
        this.set('modal_content', 'There was an error logging you in: ' + error);
      }
      Ember.Logger.error(error);
      Ember.$('#appmodal').openModal();
    },
    invalidate_session: function() {
      this.get('session').invalidate();
    }
  },

  me: function() {
    return this.store.find("user", this.get("session.data.authenticated.id"));
  }.property("session.data.authenticated.id"),

  background_change: function() {
    var view = this.get("view");
    if (view === "iframe") {
      Ember.$('body').addClass("iframe");
    } else {
      Ember.$('body').removeClass("iframe");
    }
  }.observes("view")
});
