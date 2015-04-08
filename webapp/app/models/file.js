import DS from 'ember-data';
/* global moment */

export default DS.Model.extend({
  beam: DS.belongsTo("beam"),
  file_name: DS.attr("string"),
  status: DS.attr("string"),
  size: DS.attr("number"),

  link: function() {
    return '/file_contents/' + this.get('id');
  }.property('id'),
});
