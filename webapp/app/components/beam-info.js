import Ember from 'ember';

const limit = 50;

export default Ember.Component.extend({
  session: Ember.inject.service('session'),
  store: Ember.inject.service('store'),
  pinned: false,
  pages: 1,
  files: [],
  back: false,
  iframe: false,
  editing_comment: false,
  created: false,
  text_file_filter: "",

  didInsertElement: function() {
    if (this.get("extended")) {
      this.set("created", true);
      this.set("text_file_filter", this.get("file_filter"));
    }
  },

  update_textbox: function() {
    this.set("text_file_filter", this.get("file_filter"));
  }.observes("file_filter"),

  get_files: async function() {
    const query = {
      offset: (Math.max(0, this.get("page") - 1)) * limit,
      limit: limit,
      filter: this.get("file_filter"),
      beam_id: this.get("model.id")
    };

    try {
      const response = await this.get("store").query('file', query);
      this.set("files", response);

      if (response.meta.total > 0) {
        const pages = Math.ceil(response.meta.total / limit);
        this.set("pages", pages);
        if (this.get("page") > pages) {
          this.set("page", pages);
        }
      } else {
        this.set("pages", 0);
      }
    } catch (error) {
      Ember.Logger.error(error);
    }
  }.observes("file_filter", "model", "page", "created"),

  display_pagination: function() {
    return this.get("pages") > 1;
  }.property("pages"),

  iter_pages: function () {
    const pages = this.get("pages");
    let arr = new Array(pages);
    for (let i=1; i <= pages; ++i) {
      arr[i - 1] = i;
    }
    return arr;
  }.property("pages"),

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
    },
    clean: function() {
      this.set("file_filter", "");
      this.set("text_file_filter", "");
    },
    toggleEditing: function() {
      const editing_comment = this.get("editing_comment");
      if (editing_comment) {
        this.get("model").save();
      }
      this.set("editing_comment", !editing_comment);
    },
    changeFilter: function() {
      this.set("file_filter", this.get("text_file_filter"));
    }
  }
});
