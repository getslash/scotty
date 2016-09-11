import Ember from 'ember';

export default Ember.Component.extend({
  actions: {
    remove_issue: function(issue) {
      this.sendAction("remove_issue", issue);
    }
  }
});
