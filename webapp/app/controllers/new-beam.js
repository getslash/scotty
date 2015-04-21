import Ember from "ember";

export default Ember.Controller.extend({
  user: "",
  host: "",
  directory: "",
  ssh_key: "",
  password: "",
  submitting: false,
  auth_rsa: true,
  auth_password: false,

  disable_all: function() {
    this.set("auth_rsa", false);
    this.set("ssh_key", "");
    this.set("auth_password", false);
    this.set("password", "");
  },

  actions: {
    beam: function() {
      if (this.get("submitting")) {
        return;
      }

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
      this.set("submitting", true);

      var auth_method = "";
      if (this.get("auth_rsa")) {
        auth_method = "rsa";
      } else if (this.get("auth_password")) {
        auth_method = "password";
      } else {
        throw "Invalid mode";
      }

      var beam = this.store.createRecord("beam", {
        host: this.get("host"),
        ssh_key: this.get("ssh_key"),
        password: this.get("password"),
        auth_method: auth_method,
        user: this.get("user"),
        directory: this.get("directory"),
      });

      var self = this;
      beam.save()
        .then(
          function() {
            self.set("submitting", false);
            self.set("ssh_key", "");
            self.transitionTo("beam", beam.id);
          },
          function(response) {
            self.set("submitting", false);
            self.set("error", response.statusText);
          }
      );
    },
    method_rsa: function() {
      this.disable_all();
      this.set("auth_rsa", true);
    },
    method_password: function() {
      this.disable_all();
      this.set("auth_password", true);
    }
  }
});
