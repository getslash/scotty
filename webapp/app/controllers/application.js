import Ember from 'ember';

export default Ember.Controller.extend({
  modal_content: "",
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
    return this.store.find("user", this.get("session.id"));
  }.property("session.id"),
});
