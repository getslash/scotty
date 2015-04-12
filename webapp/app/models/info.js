import DS from 'ember-data';
import Ember from 'ember';

var inflector = Ember.Inflector.inflector;
inflector.uncountable('info');

export default DS.Model.extend({
  version: DS.attr("string")
});
