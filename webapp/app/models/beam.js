import Ember from 'ember';
import DS from 'ember-data';
/* global moment */

export default DS.Model.extend({
  start: DS.attr('date'),
  size: DS.attr('number'),
  host: DS.attr('string'),
  ssh_key: DS.attr('string'),
  auth_method: DS.attr('string'),
  password: DS.attr('string'),
  user: DS.attr('string'),
  directory: DS.attr('string'),
  comment: DS.attr('string'),
  deleted: DS.attr('boolean'),
  purge_time: DS.attr('number'),
  type: DS.attr('string'),
  error_message: DS.attr('string'),
  completed: DS.attr('boolean'),
  tags: DS.attr('tags'),
  files: DS.attr(),
  initiator: DS.belongsTo('user', {
    async: true
  }),
  pins: DS.hasMany('user', {
    async: true
  }),
  associated_issues: DS.hasMany('issue', {
    async: true
  }),
  pinners: "",
  tick: 1,

  relative_time: function() {
    return moment(this.get("start")).fromNow();
  }.property("start", "tick"),

  purge_str: function() {
    var purge_time = this.get("purge_time");

    if (purge_time === 0) {
      return "today";
    } else if (purge_time === 1) {
      return "in 1 day";
    } else {
      return "in " + purge_time + " days";
    }
  }.property("purge_today").readOnly(),

  should_display_purge_str: function() {
    return this.get("purge_time") != null;
  }.property("has_pinners", "completed").readOnly(),

  num_of_pins: function() {
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
      self.set("pinners", pins.map(function(p) {
        return p.get("name");
      }).toArray().join(", "));
    });
  },

  img: function() {
    return (this.get("completed") ? (this.get("error_message") != null ? "/static/assets/img/folder-error.gif" : "/static/assets/img/folder-regular.gif") : "/static/assets/img/folder-beaming.gif");
  }.property("completed", "error_message")
});
