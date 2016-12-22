import Ember from 'ember';

export default Ember.Controller.extend({
  modalContent: "",
  session: Ember.inject.service('session'),

  iframe: function() {
    return this.get("view") === "iframe";
  }.property("view"),

  actions: {
    loginError: function(error) {
      this.set('modalContent', 'There was an error logging you in: ' + error);
      Ember.Logger.error(error);
      Ember.$('#appmodal').openModal();
    },
    logout: function() {
      this.get('session').invalidate();
    }
  },

  me: function() {
    return this.store.find("user", this.get("session.data.authenticated.id"));
  }.property("session.data.authenticated.id")
});
