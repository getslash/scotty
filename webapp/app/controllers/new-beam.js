import Ember from "ember";
import { task } from 'ember-concurrency';

export default Ember.Controller.extend({
  user: "",
  host: "",
  directory: "",
  ssh_key: "",
  password: "",
  auth_rsa: false,
  auth_password: false,
  auth_stored_key: true,
  tags: "",
  selected_key: null,

  clear_auth_fields: function() {
    this.set("auth_rsa", false);
    this.set("ssh_key", "");
    this.set("auth_password", false);
    this.set("auth_stored_key", false);
    this.set("password", "");
  },

  model_change: function() {
    this.set("selected_key", this.get("model.firstObject"));
  }.observes("model"),

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
    } else if (this.get("auth_stored_key")) {
      auth_method = "stored_key";
      if (this.get("stored_key") === null) {
        this.set("error", "No stored key selected");
        return;
      }
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
      stored_key: this.get("selected_key"),
      tags: this.get("tags").split(",")
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
    this.set("auth_stored_key", true);
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
    },
    method_stored_key: function() {
      this.clear_auth_fields();
      this.set("auth_stored_key", true);
    },
    key_select: function(selected_key) {
      this.set("selected_key", selected_key);
    }
  }
});
