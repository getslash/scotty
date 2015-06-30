import DS from 'ember-data';

export default DS.RESTSerializer.extend({
  keyForAttribute: function(key, method) {
    if (key === "error_message") {
      return "error";
    } else {
      return this._super(key, method);
    }
  }
});
