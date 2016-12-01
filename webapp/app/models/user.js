import DS from 'ember-data';

export default DS.Model.extend({
  name: DS.attr('string'),
  email: DS.attr('string'),
  displayName: function() {
    if (this.get('name')) {
      return this.get('name');
    }

    if (this.get('email')) {
      return this.get('email');
    }

    return "...";
  }.property("name", "email")
});
