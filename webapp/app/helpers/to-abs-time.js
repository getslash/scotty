import Ember from 'ember';
/* global moment */

export function toAbsTime(input) {
  return moment(input.toString(), 'X').format('DD/MM/YY HH:mm');
}

export default Ember.Handlebars.makeBoundHelper(toAbsTime);
