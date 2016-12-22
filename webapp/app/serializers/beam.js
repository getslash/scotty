import Ember from 'ember';
import DS from 'ember-data';

export default DS.RESTSerializer.extend({
  keyForAttribute: function(attr) {
    return Ember.String.underscore(attr);
  },
  keyForRelationship: function(link) {
    return Ember.String.underscore(link);
  },

  attrs: {
    errorMessage: "error"
  }
});
