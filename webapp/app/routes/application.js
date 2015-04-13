import Ember from 'ember';

import ApplicationRouteMixin from 'simple-auth/mixins/application-route-mixin';


export default Ember.Route.extend(ApplicationRouteMixin, {
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
