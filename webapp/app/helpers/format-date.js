import Ember from 'ember';

/* global moment */

export function formatDate(params/*, hash*/) {
  return moment(params[0]).format('DD/MM/YY HH:mm');
}

export default Ember.Helper.helper(formatDate);
