import Ember from 'ember';

export default Ember.Controller.extend({
  pinned: false,

  reloadModel: function() {
    this.get("model").reload();
  }.observes("model"),

  monitor_pins: function() {
    Ember.Logger.info("Observerd " + this.get("model.id"));
    Ember.run.once(this, "update_pinned");
  }.observes("model.pins", "session.id").on("init"),

  update_pinned: function() {
    Ember.Logger.info("Checking pin state for " + this.get("model.id"));
    if (this.get("session.id") === undefined) {
      this.set("pinned", false);
    } else {
      var self = this;
      return this.store.find("user", this.get("session.id")).then(function(me) {
        self.set("pinned", self.get("model.pins").contains(me));
      });
    }
  },

  actions: {
    pin: function(pinned, force) {
      var self = this;
      Ember.$.ajax({
        type: "put",
        url: "/pin",
        contentType : 'application/json',
        data: JSON.stringify({ beam_id: this.get("model.id"), should_pin: !pinned})
      }).then(function() {
        return self.store.fetchById("beam", self.get("model.id"));
      });
    }
  }
});
