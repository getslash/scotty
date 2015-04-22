import Ember from 'ember';

export default Ember.Mixin.create({
  afterModel: function() {
    Ember.run.scheduleOnce('afterRender', function() {
      Ember.$('.tooltipped').tooltip({delay: 50});
    });
  }
});
