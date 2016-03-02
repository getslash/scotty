import Ember from 'ember';
import ApplicationRouteMixin from 'ember-simple-auth/mixins/application-route-mixin';
import { task, timeout } from 'ember-concurrency';

export default Ember.Route.extend(ApplicationRouteMixin, {
  actions: {
    login: function() {
      var self = this;

      this.get('torii').open('google-oauth2').then(function(authorization) {
          return self.get('session').authenticate('authenticator:token', authorization).then(
            function(data) {
              return data;
            },
            function(error) {
              self.controllerFor('application').send('login_error', error);
            }
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
        info.type = "info";
        self.store.push({
          data: info
        });
        return info;
      });
    }

    return this.store.find("info", "1");
  },

  relative_time_update: task(function * () {
    for (;;) {
      Ember.Logger.info("yi");
      let beams = this.store.peekAll("beam").content;
      for (var i = 0; i < beams.length; i++) {
        let beam = beams[i].getRecord();
        beam.set("tick", beam.get("tick") + 1);
      }

      yield timeout(60000);
    }
  }).on("init")
});
