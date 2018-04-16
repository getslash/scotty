import Component from '@ember/component';

export default Component.extend({
  adding: false,
  tracker: null,

  didReceiveAttrs: function() {
    this.set("tracker", this.get("trackers.firstObject"));
  },

  actions: {
    remove: function(issue) {
      this.get("onRemoval")(issue);
    },
    click: function() {
      this.set("adding", true);
    },
    toggle: function(submit) {
      const idInTracker = this.get("idInTracker");
      if (submit && idInTracker) {
        this.get("onAssign")(this.get("tracker"), idInTracker);
      }
      this.set("adding", false);
    }
  }
});
