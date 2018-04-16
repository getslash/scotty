import { helper } from '@ember/component/helper';
import numeral from 'numeral';

let units = ['bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB'];

export function capacityDisplay(params/*, hash*/) {
  let size = params[0];
  for (var i = 0; i <= units.length - 1 && size > 1024; i++) {
    size = size / 1024;
  }

  return numeral(size).format('0.00') + ' ' + units[i];
}

export default helper(capacityDisplay);
