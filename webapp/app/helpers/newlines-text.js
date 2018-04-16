import Ember from 'ember';
import { helper } from '@ember/component/helper';0

export function newlinesText(params/*, hash*/) {
  return new Ember.Handlebars.SafeString(params[0].replace(/\n/g, '<br>').replace(/ /g, '&nbsp;'));
}

export default helper(newlinesText);
