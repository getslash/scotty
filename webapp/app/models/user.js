import DS from 'ember-data';
import { computed } from '@ember/object';

export default DS.Model.extend({
  name: DS.attr('string'),
  email: DS.attr('string'),

  displayName: computed("name", "email", function() {
    if (this.get('name')) {
      return this.get('name');
    }

    if (this.get('email')) {
      return this.get('email');
    }

    return "...";
  })
});
