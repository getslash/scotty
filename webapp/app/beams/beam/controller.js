import Ember from 'ember';
import { task } from 'ember-concurrency';

export default Ember.Controller.extend({
  session: Ember.inject.service('session'),
  queryParams: ['filePage', 'fileFilter'],
  filePage: 1,
  fileFilter: null,

  removeIssue: task(function * (issue) {
    const model = this.get("model");
    const beamId = this.get("model.beam.id");
    yield Ember.$.ajax({
      type: "delete",
      url: `/beams/${beamId}/issues/${issue.id}`});
    model.beam.reload();
  }),

  assignIssue: task(function * (tracker, issueName) {
    const model = this.get("model");
    const beamId = this.get("model.beam.id");
    const issue = this.get("store").createRecord(
      "issue",
      {
        trackerId: tracker.id,
        idInTracker: issueName
      }
    );

    yield;
    yield issue.save();
    yield Ember.$.ajax({
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
