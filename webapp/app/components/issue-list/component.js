import Ember from 'ember';

export default Ember.Component.extend({
  actions: {
    confirm: function(issue) {
      this.get("on_issue_removal")(issue);
    }
  }
});
