import Component from '@ember/component';
import { inject } from '@ember/service';
import { computed, observer } from '@ember/object';
import { task } from 'ember-concurrency';

const FILES_PER_PAGE = 20;

export default Component.extend({
  store: inject(),
  pages: 1,
  total: 0,

  sortKeys: ['name:desc'],
  sortedModel: computed.sort('files', 'sortKeys'),

  pagesList: computed("pages", function () {
    const pages = this.pages;
    let arr = new Array(pages);
    for (let i=1; i <= pages; ++i) {
      arr[i - 1] = i;
    }
    return arr;
  }),

  getFiles: task(function * () {
    const query = {
      offset: (Math.max(0, this.page - 1)) * FILES_PER_PAGE,
      limit: FILES_PER_PAGE,
      filter: this.fileFilter,
      beam_id: this.get("model.beam.id")
    };

    const response = yield this.store.query('file', query);
    this.set("files", response);

    this.set("total", response.meta.total);
    if (response.meta.total > 0) {
      const pages = Math.ceil(response.meta.total / FILES_PER_PAGE);
      this.set("pages", pages);
      if (this.page > pages) {
        this.set("page", pages);
      }
    } else {
      this.set("pages", 0);
    }
  }).restartable(),

  didReceiveAttrs() {
    this._super(...arguments);
    this.getFiles.perform();
  },

  watchFileProperties: observer("fileFilter", "page", "model.beam.files", function() {
    this.getFiles.perform();
  }),

  didInsertElement() {
    this.set("filterValue", this.fileFilter);
  },

  updateSearchbox: observer("fileFilter", function() {
    this.set("filterValue", this.fileFilter);
  }),

  actions: {
    filterChange: function(newFilter) {
      this.set("fileFilter", newFilter);
    },
    sortBy: function(property, acsending) {
      let method = (acsending) ? 'asc': 'desc';
      this.sortKeys.pop()
      this.sortKeys.pushObject(`${property}:${method}`);
    }
  }
});
