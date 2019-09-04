import Route from '@ember/routing/route';
import ApplicationRouteMixin from 'ember-simple-auth/mixins/application-route-mixin';
import $ from 'jquery';

export default Route.extend(ApplicationRouteMixin, {
  routeAfterAuthentication: null,

  model: function() {
    var self = this;
    if (!this.store.hasRecordForId("info", "1")) {
      return $.getJSON("/info").then(function(info) {
        info.id = 1;
        info.type = "info";
        self.store.push({
          data: info
        });
        return info;
      });
    }

    return this.store.find("info", "1");
  },

  actions: {
    login: function() {
      var self = this;

      this.get('torii').open('google-oauth2').then(function(authorization) {
        return self.get('session').authenticate('authenticator:token', authorization).then(
          function(data) {
            return data;
          },
          function(error) {
            self.controllerFor('application').send('loginError', error);
          }
        );
      },
      function(error) {
        self.controllerFor('application').send('loginError', error);
      });
    },

    scottyClicked: function() {
      this.transitionTo("beams", {queryParams: {tag: null, uid: null, email: null, page: null}});
    }
  }
});
