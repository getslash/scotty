import Ember from 'ember';
import ApplicationRouteMixin from 'simple-auth/mixins/application-route-mixin';


export default Ember.Route.extend(ApplicationRouteMixin, {
  actions: {
    login: function() {
      var self = this;

      this.get('torii').open('google-oauth2').then(function(authorization) {
        return self.get('session').authenticate('authenticator:token', authorization).then(
          function(data) { return data; },
          function(error) { self.controllerFor('application').send('login_error', error); }
        );
      },
      function(error) {
        self.controllerFor('application').send('login_error', error);
      });
    },
    scottyButton: function() {
      this.transitionTo("index");
    }
  },
  model: function() {
    var self = this;
    if (!this.store.recordIsLoaded("info", "1")) {
      return Ember.$.getJSON("/info").then(function(info) {
        info.id = 1;
        self.store.push("info", info);
        return info;
      });
    }

    return this.store.find("info", "1");
  }
});
