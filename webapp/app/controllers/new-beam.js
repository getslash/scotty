import Ember from "ember";

export default Ember.Controller.extend({
  user: "vagrant",
  host: "192.168.50.4",
  directory: "/home/vagrant",
  ssh_key: "",
  submitting: false,

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

      if (!this.get("ssh_key")) {
        this.set("error", "SSH key field cannot be empty");
        Ember.$("#ssh_key").focus();
        return;
      }

      this.set("error", "");
      this.set("submitting", true);

      var beam = this.store.createRecord("beam", {
        host: this.get("host"),
        ssh_key: this.get("ssh_key"),
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
    }
  }
});
