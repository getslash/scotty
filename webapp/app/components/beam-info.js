import Ember from 'ember';

export default Ember.Component.extend({
  session: Ember.inject.service('session'),
  store: Ember.inject.service('store'),
  pinned: false,
  limit: 50,
  page: 1,
  back: false,
  iframe: false,
  file_filter: "",

  filtered_model: function() {
    var model = this.get("model.files");
    if (this.get("file_filter")) {
      let file_filter = this.get("file_filter");
      model = model.filter(function(f) {
        return f.get("file_name").indexOf(file_filter) !== -1;
      });
    }
    return model;
  }.property("file_filter"),

  sliced_files: function() {
    let limit = this.get("limit");
    let page = this.get("page") - 1;
    return this.get("filtered_model").slice(limit * page, limit * (page + 1));
  }.property("limit", "page", "filtered_model"),

  display_pagination: function() {
    return this.get("pages").length > 1;
  }.property("pages"),

  pages: function() {
    var arr = [];
    for (var i = 1; i <= Math.ceil(this.get("filtered_model.length") / this.get("limit")); ++i) {
      arr.push(i);
    }

    let last_page = arr[arr.length - 1];
    Ember.Logger.info("last page: " + last_page);
    if (this.get("page") > last_page) {
      this.set("page", last_page);
    }

    return arr;
  }.property("filtered_model", "limit"),

  monitor_pins: function() {
    Ember.run.once(this, "update_pinned");
  }.observes("model.pins", "session.data.authenticated.id").on("init"),

  update_pinned: function() {
    let store = this.get("store");

    if (this.get("session.data.authenticated.id") === undefined) {
      this.set("pinned", false);
    } else {
      var self = this;
      return store.find("user", this.get("session.data.authenticated.id")).then(function(me) {
        self.set("pinned", self.get("model.pins").contains(me));
      });
    }
  },

  actions: {
    pin: function(pinned) {
      let store = this.get("store");
      let id = this.get("model.id");
      Ember.$.ajax({
        type: "put",
        url: "/pin",
        contentType: 'application/json',
        data: JSON.stringify({
          beam_id: parseInt(this.get("model.id")),
          should_pin: !pinned
        })
      }).then(function() {
        return store.findRecord("beam", id, {reload: true}).then(function() {
          Ember.run.scheduleOnce('afterRender', function() {
            Ember.$('.tooltipped').tooltip({
              delay: 50
            });
          });
        });
      });
    },
    back: function() {
      window.history.go(-1);
    }
  }
});
