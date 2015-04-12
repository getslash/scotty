import DS from 'ember-data';

var inflector = Ember.Inflector.inflector;
inflector.uncountable('info');

export default DS.Model.extend({
  version: DS.attr("string")
});
