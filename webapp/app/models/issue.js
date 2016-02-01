import DS from 'ember-data';

export default DS.Model.extend({
  open: DS.attr('boolean'),
  id_in_tracker: DS.attr('string'),
  url: DS.attr('string')
});
