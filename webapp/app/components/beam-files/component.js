import Component from '@ember/component';
import { inject } from '@ember/service';
import { computed, observer } from '@ember/object';
import { task } from 'ember-concurrency';

const FILES_PER_PAGE = 20;

export default Component.extend({
  store: inject(),
  pages: 1,
  total: 0,

  pagesList: computed("pages", function () {
    const pages = this.get("pages");
    let arr = new Array(pages);
    for (let i=1; i <= pages; ++i) {
      arr[i - 1] = i;
    }
    return arr;
  }),

  getFiles: task(function * () {
    const query = {
      offset: (Math.max(0, this.get("page") - 1)) * FILES_PER_PAGE,
      limit: FILES_PER_PAGE,
      filter: this.get("fileFilter"),
      beam_id: this.get("model.beam.id")
    };

    const response = yield this.get("store").query('file', query);
    this.set("files", response);

      this.set("total", response.meta.total);
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

  watchFileProperties: observer("fileFilter", "page", "model.beam.files", function() {
    this.get("getFiles").perform();
  }),

  didInsertElement() {
    this.set("filterValue", this.get("fileFilter"));
  },

  updateSearchbox: observer("fileFilter", function() {
    this.set("filterValue", this.get("fileFilter"));
  }),

  actions: {
    filterChange: function(newFilter) {
      this.set("fileFilter", newFilter);
    }
  }
});
