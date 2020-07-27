import DS from 'ember-data';
import { computed } from '@ember/object';

export default DS.Model.extend({
  name: DS.attr('string'),
  email: DS.attr('string'),

  displayName: computed("name", "email", function() {
    if (this.name) {
      return this.name;
    }

    if (this.email) {
      return this.email;
    }

    return "...";
  })
});
