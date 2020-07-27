import Controller from '@ember/controller';
import { computed } from '@ember/object';
import { inject } from '@ember/service';
import Ember from 'ember';
import $ from 'jquery';

export default Controller.extend({
  modalContent: "",
  session: inject('session'),

  iframe: computed.equal('view', "iframe"),

  actions: {
    loginError: function(error) {
      this.set('modalContent', 'There was an error logging you in: ' + error);
      Ember.Logger.error(error);
      $('#appmodal').openModal();
    },
    logout: function() {
      this.session.invalidate();
    }
  },

  me: computed('session.data.authenticated.id', 'store', function() {
    return this.store.find("user", this.get("session.data.authenticated.id"));
  })
});
