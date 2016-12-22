import Ember from 'ember';
import ApplicationRouteMixin from 'ember-simple-auth/mixins/application-route-mixin';
import { task, timeout } from 'ember-concurrency';

export default Ember.Route.extend(ApplicationRouteMixin, {

  model: function() {
    var self = this;
    if (!this.store.recordIsLoaded("info", "1")) {
      return Ember.$.getJSON("/info").then(function(info) {
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

  updateRelativeTime: task(function * () {
    for (;;) {
      let beams = this.store.peekAll("beam").content;
      for (var i = 0; i < beams.length; i++) {
        let beam = beams[i].getRecord();
        beam.set("tick", beam.get("tick") + 1);
      }

      yield timeout(60000);
    }
  }).on("init"),

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
      this.transitionTo("beams", {queryParams: {tag: null, uid: null, email: null}});
    }
  }
});
