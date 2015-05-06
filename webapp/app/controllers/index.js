import Ember from 'ember';

export default Ember.ArrayController.extend({
  itemController: 'beam',
  sortProperties: ['start'],
  sortAscending: false,
  needs: "application"
});
