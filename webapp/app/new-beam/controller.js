import Object from '@ember/object';
import Controller from '@ember/controller';
import { observer } from '@ember/object';
import { task } from 'ember-concurrency';
import $ from 'jquery';

const Auth = Object.extend({
  method: "storedKey",
  key: "",
  password: "",
  storedKey: "",

  getAuthMethod: function() {
    switch (this.method) {
    case "key":
      return "rsa";
    case "storedKey":
      return "stored_key";
    case "password":
      return "password";
    }

    throw "Invalid mode";
  }
});

export default Controller.extend({
  auth: Auth.create(),
  user: "",
  host: "",
  directory: "",
  tags: [],

  modelChange: observer("model", function() {
    const model = this.model;
    if (model.get("length") > 0) {
      this.set("auth.storedKey", model.objectAt(0));
    }
  }),

  beamUp: task(function * () {
    const authMethod = this.auth.getAuthMethod();

    const beam = this.store.createRecord("beam", {
      host: this.host,
      sshKey: this.get("auth.key"),
      password: this.get("auth.password"),
      authMethod: authMethod,
      user: this.user,
      directory: this.directory,
      storedKey: this.get("auth.storedKey"),
      tags: this.tags
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
      if (!this.user) {
        this.set("error", "User field cannot be empty");
        $("#user").focus();
        return;
      }

      if (!this.host) {
        this.set("error", "Host field cannot be empty");
        $("#host").focus();
        return;
      }

      if (!this.directory) {
        this.set("error", "Directory field cannot be empty");
        $("#directory").focus();
        return;
      }

      if (this.get("auth.method") === "key" && (!this.get("auth.key"))) {
        this.set("error", "SSH key field cannot be empty");
        $("#key").focus();
        return;
      }

      if (this.get("auth.method") === "password" && (!this.get("auth.password"))) {
        this.set("error", "Password cannot be empty");
        $("#password").focus();
        return;
      }

      this.beamUp.perform();
    }
  }
});
