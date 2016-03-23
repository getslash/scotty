import Ember from "ember";
import { task } from 'ember-concurrency';

export default Ember.Controller.extend({
  user: "",
  host: "",
  directory: "",
  ssh_key: "",
  password: "",
  auth_rsa: false,
  auth_password: true,
  tags: "",

  clear_auth_fields: function() {
    this.set("auth_rsa", false);
    this.set("ssh_key", "");
    this.set("auth_password", false);
    this.set("password", "");
  },

  beam: task(function * () {
    if (!this.get("user")) {
      this.set("error", "User field cannot be empty");
      Ember.$("#user").focus();
      return;
    }

    if (!this.get("host")) {
      this.set("error", "Host field cannot be empty");
      Ember.$("#host").focus();
      return;
    }

    if (!this.get("directory")) {
      this.set("error", "Directory field cannot be empty");
      Ember.$("#directory").focus();
      return;
    }

    if (this.get("auth_rsa") && (!this.get("ssh_key"))) {
      this.set("error", "SSH key field cannot be empty");
      Ember.$("#ssh_key").focus();
      return;
    }

    this.set("error", "");

    var auth_method = "";
    if (this.get("auth_rsa")) {
      auth_method = "rsa";
    } else if (this.get("auth_password")) {
      auth_method = "password";
    } else {
      throw "Invalid mode";
    }

    const beam = this.store.createRecord("beam", {
      host: this.get("host"),
      ssh_key: this.get("ssh_key"),
      password: this.get("password"),
      auth_method: auth_method,
      user: this.get("user"),
      directory: this.get("directory"),
      tags: this.get("tags").split(","),
    });

    try {
      yield beam.save();
    } catch(err) {
      const response = err.errors[0];
      var msg = '';
      switch (response.status) {
      case "409":
        msg = response.detail;
        break;
      case "403":
        msg = "Your session logged out. Please refresh the application.";
        break;
      default:
        msg = response.statusText || response.message;
      }
      this.set("error", msg);
      return;
    }

    this.clear_auth_fields();
    this.set("auth_password", true);
    this.transitionToRoute("beam", beam.id);

  }).drop(),

  actions: {
    method_rsa: function() {
      this.clear_auth_fields();
      this.set("auth_rsa", true);
    },
    method_password: function() {
      this.clear_auth_fields();
      this.set("auth_password", true);
    }
  }
});
