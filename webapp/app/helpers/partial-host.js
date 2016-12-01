import Ember from 'ember';

export function partialHost([value]) {
  return value.split(".")[0];
}

export default Ember.Helper.helper(partialHost);
