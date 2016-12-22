import Ember from 'ember';

export function fileName([value]) {
  if (value.startsWith("./")) {
    return value.slice(2);
  }
  return value;
}

export default Ember.Helper.helper(fileName);
