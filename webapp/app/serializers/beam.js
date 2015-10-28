import DS from 'ember-data';

export default DS.RESTSerializer.extend({
  attrs: {
    error_message: "error",
  }
});
