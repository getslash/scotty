import Ember from 'ember';

/* global moment */

export function formatDate(params/*, hash*/) {
  if (params[0] === null) {
    return '';
  }
  return moment(params[0]).format('DD/MM/YY HH:mm');
}

export default Ember.Helper.helper(formatDate);
