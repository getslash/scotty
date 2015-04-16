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

    img: function() {
      return this.get("completed") ? "/static/assets/img/folder-regular.gif" : "/static/assets/img/folder-beaming.gif";
    }.property("completed")
});
