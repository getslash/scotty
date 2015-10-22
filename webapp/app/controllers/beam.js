import Ember from 'ember';

export default Ember.Controller.extend({
  queryParams: ['page', 'back'],
  pinned: false,
  back: false,
  needs: "application",
  limit: 50,
  page: 1,
  file_filter: "",
  session: Ember.inject.service('session'),


  reloadModel: function() {
    this.get("model").reload();
  }.observes("model"),

  sliced_files: function() {
    var limit = this.get("limit");
    var page = this.get("page") - 1;
    var model = this.get("model.files");
    if (this.get("file_filter")) {
      var file_filter = this.get("file_filter");
      model = model.filter(function(f) {
        return f.get("file_name").indexOf(file_filter) !== -1;
      });
    }
    return model.slice(limit * page, limit * (page + 1));
  }.property("limit", "page", "model.files", "file_filter"),

  display_pagination: function() {
    return this.get("model.files.length") > this.get("limit");
  }.property("limit", "model.files.length"),

  pages: function() {
    var arr = [];
    for (var i = 1; i <= Math.ceil(this.get("model.files.length") / this.get("limit")); ++i) {
      arr.push(i);
    }
    return arr;
  }.property("model.files.length", "limit"),

  monitor_pins: function() {
    Ember.run.once(this, "update_pinned");
  }.observes("model.pins", "session.data.secure.id").on("init"),

  update_pinned: function() {
    if (this.get("session.data.secure.id") === undefined) {
      this.set("pinned", false);
    } else {
      var self = this;
      return this.store.find("user", this.get("session.data.secure.id")).then(function(me) {
        self.set("pinned", self.get("model.pins").contains(me));
      });
    }
  },

  actions: {
    pin: function(pinned) {
      var self = this;
      Ember.$.ajax({
        type: "put",
        url: "/pin",
        contentType: 'application/json',
        data: JSON.stringify({
          beam_id: parseInt(this.get("model.id")),
          should_pin: !pinned
        })
      }).then(function() {
        return self.store.fetchById("beam", self.get("model.id")).then(function() {
          Ember.run.scheduleOnce('afterRender', function() {
            Ember.$('.tooltipped').tooltip({
              delay: 50
            });
          });
        });
      });
    }
  }
});
