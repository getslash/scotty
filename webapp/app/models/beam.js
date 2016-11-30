import DS from 'ember-data';
/* global moment */

export default DS.Model.extend({
  start: DS.attr('date'),
  size: DS.attr('number'),
  host: DS.attr('string'),
  sshKey: DS.attr('string'),
  storedKey: DS.belongsTo('key'),
  authMethod: DS.attr('string'),
  password: DS.attr('string'),
  user: DS.attr('string'),
  directory: DS.attr('string'),
  comment: DS.attr('string'),
  deleted: DS.attr('boolean'),
  purgeTime: DS.attr('number'),
  type: DS.attr('string'),
  errorMessage: DS.attr('string'),
  completed: DS.attr('boolean'),
  tags: DS.attr('tags'),
  files: DS.attr(),
  initiator: DS.belongsTo('user', {
    async: true
  }),
  pins: DS.hasMany('user', {
    async: true
  }),
  associatedIssues: DS.hasMany('issue', {
    async: true
  }),
  pinners: "",
  tick: 1,

  relativeTime: function() {
    return moment(this.get("start")).fromNow();
  }.property("start", "tick")
});
