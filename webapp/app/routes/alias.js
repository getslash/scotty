import Ember from 'ember';

export default Ember.Route.extend({
  beforeModel: function(transition) {
    var self = this;
    return Ember.$.getJSON("/alias/" + transition.params.alias.alias_id).then(function(alias) {
      return self.transitionTo("beam", alias.beam_id);
    });
  },
});
