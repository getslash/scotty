import Ember from 'ember';

var units = ['bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB'];

export function capacityDisplay(input) {
  var i = 0;
  for (i = 0; i <= units.length - 1 && input > 1024; i++) {
    input = input / 1024;
  }

  return numeral(input).format('0.00') + ' ' + units[i];
}

export default Ember.Handlebars.makeBoundHelper(capacityDisplay);
