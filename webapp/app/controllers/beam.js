import Ember from 'ember';

export default Ember.Controller.extend({
  queryParams: ['page', 'back', 'file_filter'],
  back: false,
  page: 1,
  application: Ember.inject.controller('application'),

  reloadModel: function() {
    this.get("model").reload();
  }.observes("model"),
});
