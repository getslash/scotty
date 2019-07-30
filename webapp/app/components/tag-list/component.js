import Component from '@ember/component';

export default Component.extend({
  actions: {
    modify: function(modifying) {
      this.set('modifying', modifying);
    },
    add: function(tag){
      this.tagList.addTag(tag);
    }
  }
});
