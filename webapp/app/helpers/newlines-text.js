import Ember from 'ember';

export function newlinesText(params) {
  return new Ember.Handlebars.SafeString(params[0].replace(/\n/g, '<br>').replace(/ /g, '&nbsp;'));
}

export default Ember.HTMLBars.makeBoundHelper(newlinesText);