import DS from 'ember-data';

export default DS.Model.extend({
  open: DS.attr('boolean'),
  idInTracker: DS.attr('string'),
  trackerId: DS.attr('number'),
  url: DS.attr('string')
});
