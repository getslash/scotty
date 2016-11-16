import Ember from 'ember';

export function partialHost(params/*, hash*/) {
  params[0] = params[0].split(".")[0];
  return params;
}

export default Ember.Helper.helper(partialHost);
