import Ember from 'ember';
import DS from 'ember-data';

export default DS.Model.extend({
    start: DS.attr('date'),
    size: DS.attr('number'),
    host: DS.attr('string'),
    ssh_key: DS.attr('string'),
    user: DS.attr('string'),
    directory: DS.attr('string'),
    pending_deletion: DS.attr('boolean'),
    completed: DS.attr('boolean'),
    initiator: DS.belongsTo('user', {async: true}),
    files: DS.hasMany('file'),
    pins: DS.hasMany('user', {async: true}),
    pinners: "",

    num_of_pins: function () {
      return this.get("pins").get("length");
    }.property("pins"),

    has_pinners: function() {
      return this.get("pins").get("length") > 0;
    }.property("pins"),

    pins_change: function() {
      Ember.run.once(this, "join_pinners");
    }.observes("pins"),

    join_pinners: function() {
      var self = this;
      this.get("pins").then(function(pins) {
        self.set("pinners", pins.map(function(p) { return p.get("name"); }).toArray().join());
      });
    },

    img: function() {
      return this.get("completed") ? "/static/assets/img/folder-regular.gif" : "/static/assets/img/folder-beaming.gif";
    }.property("completed")
});
