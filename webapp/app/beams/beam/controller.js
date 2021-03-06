import Controller from '@ember/controller';
import { inject as controller_inject } from '@ember/controller';
import { inject } from '@ember/service';
import $ from 'jquery';
import { task } from 'ember-concurrency';

export default Controller.extend({
  session: inject('session'),
  queryParams: ['filePage', 'fileFilter'],
  filePage: 1,
  fileFilter: null,

  parent: controller_inject('beams'),

  removeIssue: task(function * (issue) {
    const model = this.model;
    const beamId = this.get("model.beam.id");
    yield $.ajax({
      type: "delete",
      url: `/beams/${beamId}/issues/${issue.id}`});
    model.beam.reload();
  }),

  assignIssue: task(function * (tracker, issueName) {
    const model = this.model;
    const beamId = this.get("model.beam.id");
    const issue = this.store.createRecord(
      "issue",
      {
        trackerId: tracker.id,
        idInTracker: issueName
      }
    );

    yield;
    yield issue.save();
    yield $.ajax({
      type: "post",
      url: `/beams/${beamId}/issues/${issue.get("id")}`});
    model.beam.reload();
  }),

  tagChange: task(function * (newTags) {
    this.set("model.beam.tags", newTags);
    const model = this.get("model.beam");
    yield model.save();
    yield model.reload();
  }),

  actions: {
    refresh: function() {
      this.get("model.beam").reload();
    }
  }
});
