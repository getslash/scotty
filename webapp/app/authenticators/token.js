import Base from 'ember-simple-auth/authenticators/base';
import { Promise } from 'rsvp';
import $ from 'jquery';

export default Base.extend({
  restore: function(credentials) {
    return new Promise(function(resolve, reject) {
      $.ajax({
        type: "POST",
        url: "/restore",
        contentType: 'application/json',
        data: JSON.stringify(credentials)
      }).then(
        function(data) {
          resolve(data);
        },
        function(reason) {
          reject(reason.status);
        }
      );
    });
  },
  invalidate: function() {
    return $.ajax({
      type: "POST",
      url: "/logout",
    });
  },
  authenticate: function(authCode) {
    return new Promise(function(resolve, reject) {
      $.ajax({
        type: "POST",
        url: "/login",
        contentType: 'application/json',
        data: JSON.stringify(authCode)
      }).then(
        function(data) {
          resolve(data);
        },
        function(reason) {
          reject(reason.status);
        }
      );
    });
  }
});
