import DS from 'ember-data';

export default DS.Model.extend({
  beam: DS.belongsTo("beam"),
  file_name: DS.attr("string"),
  status: DS.attr("string"),
  size: DS.attr("number"),
  storage_name: DS.attr("string"),
  url: DS.attr("string"),
});
