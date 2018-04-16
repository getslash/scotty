import { helper } from '@ember/component/helper';

export function fileName([value]) {
  if (value.startsWith("./")) {
    return value.slice(2);
  }
  return value;
}

export default helper(fileName);
