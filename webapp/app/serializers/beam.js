import DS from 'ember-data';

export default DS.RESTSerializer.extend({
  attrs: {
    error_message: "error"
  },
  serialize: function(snapshot) {
    return {
      comment: snapshot.record.get("comment")
    };
  },

  serializeIntoHash: function(data, type, record, options) {
    Object.assign(data, this.serialize(record, options));
  }
});
