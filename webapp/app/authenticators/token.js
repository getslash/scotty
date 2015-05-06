import Base from 'simple-auth/authenticators/base';
import Ember from "ember";

export default Base.extend({
  restore: function(credentials) {
    return new Ember.RSVP.Promise(function(resolve, reject) {
      Ember.$.ajax({
        type: "POST",
        url: "/restore",
        contentType : 'application/json',
        data: JSON.stringify(credentials)
      }).then(
        function(data) { resolve(data); },
        function(reason) { reject(reason.status); }
      );
    });
  },
  authenticate: function(auth_code) {
    return new Ember.RSVP.Promise(function(resolve, reject) {
      Ember.$.ajax({
        type: "POST",
        url: "/login",
        contentType : 'application/json',
        data: JSON.stringify(auth_code)
      }).then(
        function(data) { resolve(data); },
        function(reason) { reject(reason.status); }
      );
    });
  }
});
