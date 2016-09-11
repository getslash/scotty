import Ember from 'ember';
import { task } from 'ember-concurrency';

export default Ember.Controller.extend({
  session: Ember.inject.service('session'),
  queryParams: ['file_page', 'file_filter'],
  file_page: 1,
  file_filter: null,

  should_display_purge_str: function() {
    return this.get("model.beam.purge_time") != null;
  }.property("model.beam.purge_time").readOnly(),

  remove_issue: task(function * (issue) {
    const model = this.get("model");
    const beam_id = this.get("model.beam.id");
    yield Ember.$.ajax({
      type: "delete",
      url: `/beams/${beam_id}/issues/${issue.id}`});
    model.beam.reload();
  }),

  assign_issue: task(function * (tracker, issue_name) {
    const model = this.get("model");
    const beam_id = this.get("model.beam.id");
    const issue = this.get("store").createRecord(
      "issue",
      {
        tracker_id: tracker.id,
        id_in_tracker: issue_name
      }
    );

    yield;
    yield issue.save();
    yield Ember.$.ajax({
      type: "post",
      url: `/beams/${beam_id}/issues/${issue.get("id")}`});
    model.beam.reload();
  }),

  actions: {
    refresh_beam: function() {
      this.get("model.beam").reload();
    }
  }
});
