import Ember from 'ember';

export function fileName(params/*, hash*/) {
  if (params[0].startsWith("./")) {
    params[0] = params[0].slice(2);
  }
  return params;
}

export default Ember.Helper.helper(fileName);
