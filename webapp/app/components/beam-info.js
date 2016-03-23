import Ember from 'ember';
import { task, timeout } from 'ember-concurrency';

const FILES_PER_PAGE = 50;
const DEBOUNCE_MS = 250;

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
  tracker: 1,
  issueId: null,

  didInsertElement: function() {
    if (this.get("extended")) {
      this.set("created", true);
      this.set("text_file_filter", this.get("file_filter"));
      this.$('select').material_select();
    }
  },

  trackers: function() {
    return this.get("store").findAll("tracker");
  }.property(),

  update_textbox: function() {
    // Change the textbox when the filter in the URL changes
    this.set("text_file_filter", this.get("file_filter"));
  }.observes("file_filter"),

  get_files: task(function * () {
    const query = {
      offset: (Math.max(0, this.get("page") - 1)) * FILES_PER_PAGE,
      limit: FILES_PER_PAGE,
      filter: this.get("file_filter"),
      beam_id: this.get("model.id")
    };

    const response = yield this.get("store").query('file', query);
    this.set("files", response);

    if (response.meta.total > 0) {
      const pages = Math.ceil(response.meta.total / FILES_PER_PAGE);
      this.set("pages", pages);
      if (this.get("page") > pages) {
        this.set("page", pages);
      }
    } else {
      this.set("pages", 0);
    }
  }).restartable(),

  watch_file_properties: function() {
    this.get("get_files").perform();
  }.observes("file_filter", "model", "page", "created", "model.files"),

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
    this.get("update_pinned").perform();
  }.observes("model.pins", "session.data.authenticated.id").on("init"),

  update_pinned: task(function * () {
    const store = this.get("store");

    if (this.get("session.data.authenticated.id") === undefined) {
      this.set("pinned", false);
    } else {
      const me = yield store.find("user", this.get("session.data.authenticated.id"));
      this.set("pinned", this.get("model.pins").contains(me));
    }
  }).drop(),

  change_file_filter: task(function * () {
    yield timeout(DEBOUNCE_MS);
    this.set("file_filter", this.get("text_file_filter"));
  }).restartable(),

  pin: task(function * (pinned) {
    yield Ember.$.ajax({
      type: "put",
      url: "/pin",
      contentType: 'application/json',
      data: JSON.stringify({
        beam_id: parseInt(this.get("model.id")),
        should_pin: !pinned
      })
    });
    yield this.get("model").reload();
    Ember.run.scheduleOnce('afterRender', function() {
      Ember.$('.tooltipped').tooltip({
        delay: 50
      });
    });
  }).restartable(),

  remove_issue: task(function * (issue) {
    const model = this.get("model");
    const beam_id = this.get("model.id");
    yield Ember.$.ajax({
      type: "delete",
      url: `/beams/${beam_id}/issues/${issue}`});
    model.reload();
  }),

  add_issue: task(function * () {
    const model = this.get("model");
    const beam_id = this.get("model.id");
    const issue = this.get("store").createRecord(
      "issue",
      {
        tracker_id: 1,
        id_in_tracker: this.get("issueIdInTracker")
      }
    );

    yield issue.save();
    yield Ember.$.ajax({
        type: "post",
        url: `/beams/${beam_id}/issues/${issue.get("id")}`});
    model.reload();
  }),

  actions: {
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
    }
  }
});
