import Ember from 'ember';
/* global moment */

export function formatDate(input) {
  return moment(input[0]).format('DD/MM/YY HH:mm');
}

export default Ember.HTMLBars.makeBoundHelper(formatDate);
