import EmberObject from '@ember/object';

export const BeamFilter = EmberObject.extend({
  init() {
    this.set('tags', []);
  },

  setTags(tags) {
    this.set("tags", tags.length > 0 ? tags.split(";") : []);
  },

  addTag(tag) {
    if (this.tags.indexOf(tag) === -1){
      this.tags.pushObject(tag);
    }
  },

  removeTag(tag) {
    this.tags.removeObject(tag);
  },

  emptyTagList() {
    this.set("tags", []);
  },

  tagsCount() {
    return this.tags.length;
  }
});

export default BeamFilter;
