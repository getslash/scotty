import Ember from 'ember';
import { task } from 'ember-concurrency';

const Auth = Ember.Object.extend({
  method: "stored_key",
  key: "",
  password: "",
  stored_key: "",

  get_auth_method: function() {
    switch (this.get("method")) {
    case "key":
      return "rsa";
    case "stored_key":
      return "stored_key";
    case "password":
      return "password";
    }

    throw "Invalid mode";
  }
});

export default Ember.Controller.extend({
  auth: Auth.create(),
  user: "",
  host: "",
  directory: "",
  tags: [],

  model_change: Ember.observer("model", function() {
    const model = this.get("model");
    if (model.get("length") > 0) {
      this.set("auth.stored_key", model.objectAt(0));
    }
  }),

  beam_up: task(function * () {
    const auth_method = this.get("auth").get_auth_method();

    const beam = this.store.createRecord("beam", {
      host: this.get("host"),
      ssh_key: this.get("auth.key"),
      password: this.get("auth.password"),
      auth_method: auth_method,
      user: this.get("user"),
      directory: this.get("directory"),
      stored_key: this.get("auth.stored_key"),
      tags: this.get("tags")
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
        msg = response.statusText || response.message || response.title;
      }
      this.set("error", msg);
      return;
    }

    this.transitionToRoute("beams.beam", beam.id);
    this.set("error", "");
  }),

  actions: {
    submit: function() {
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

      if (this.get("auth.method") === "key" && (!this.get("auth.key"))) {
        this.set("error", "SSH key field cannot be empty");
        Ember.$("#key").focus();
        return;
      }

      if (this.get("auth.method") === "password" && (!this.get("auth.password"))) {
        this.set("error", "Password cannot be empty");
        Ember.$("#password").focus();
        return;
      }

      this.get("beam_up").perform();
    },

    stuff: function(hi) {
      console.log(hi);
    }
  }
});
