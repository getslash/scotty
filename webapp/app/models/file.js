import DS from 'ember-data';

export default DS.Model.extend({
  beam: DS.belongsTo("beam"),
  fileName: DS.attr("string"),
  mtime: DS.attr('date'),
  status: DS.attr("string"),
  size: DS.attr("number"),
  storageName: DS.attr("string"),
  url: DS.attr("string")
});
