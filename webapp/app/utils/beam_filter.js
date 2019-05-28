import EmberObject from '@ember/object';

export const BeamFilter = EmberObject.extend({
  init() {
    this.set('tags', []);
  },

  setTags(tags) {
    this.set("tags", tags.length > 0 ? tags.split(";") : []);
  },

  addTag(tag) {
    if (this.get("tags").indexOf(tag) === -1){
      this.get("tags").pushObject(tag);
    }
  },

  removeTag(tag) {
    this.get("tags").removeObject(tag);
  },

  emptyTagList() {
    this.set("tags", []);
  },

  tagsCount() {
    return this.get("tags").length;
  }
});

export default BeamFilter;
