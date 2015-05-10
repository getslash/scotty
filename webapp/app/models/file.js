import DS from 'ember-data';

export default DS.Model.extend({
  beam: DS.belongsTo("beam"),
  file_name: DS.attr("string"),
  status: DS.attr("string"),
  size: DS.attr("number"),
  storage_name: DS.attr("string"),

  link: function() {
    var parts = this.get('storage_name').split('.');
    if ((parts[parts.length - 1] === "gz") && (parts[parts.length - 2] === "log")) {
      parts.pop();
    }
    return '/file_contents/' + parts.join(".");
  }.property('id'),
});
