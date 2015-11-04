import Ember from 'ember';

export default Ember.Controller.extend({
  application: Ember.inject.controller('application'),
  sortKeys: ['start:desc'],
  sortedModel: Ember.computed.sort('model', 'sortKeys')
});
