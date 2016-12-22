import Ember from 'ember';
import { task } from 'ember-concurrency';

const FILES_PER_PAGE = 20;

export default Ember.Component.extend({
  store: Ember.inject.service(),
  pages: 1,

  pagesList: function () {
    const pages = this.get("pages");
    let arr = new Array(pages);
    for (let i=1; i <= pages; ++i) {
      arr[i - 1] = i;
    }
    return arr;
  }.property("pages"),

  getFiles: task(function * () {
    const query = {
      offset: (Math.max(0, this.get("page") - 1)) * FILES_PER_PAGE,
      limit: FILES_PER_PAGE,
      filter: this.get("fileFilter"),
      beam_id: this.get("model.beam.id")
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

  didReceiveAttrs() {
    this._super(...arguments);
    this.get("getFiles").perform();
  },

  watchFileProperties: function() {
    this.get("getFiles").perform();
  }.observes("fileFilter", "page", "model.beam.files"),

  updateSearchbox: function() {
    this.set("filterValue", this.get("fileFilter"));
  }.on("init").observes("fileFilter"),

  actions: {
    filterChange: function(newFilter) {
      this.set("fileFilter", newFilter);
    }
  }
});
