import { helper } from '@ember/component/helper';

export function partialHost([value]) {
  return value.split(".")[0];
}

export default helper(partialHost);
