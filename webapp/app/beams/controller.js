import Controller from '@ember/controller';
import { observer, computed } from '@ember/object';
import { BeamFilter } from '../utils/beam_filter';


export default Controller.extend({
  tag: "",
  email: null,
  uid: null,
  tagList: BeamFilter.create(),
  queryParams: ['tag', 'email', 'uid', 'page'],
  page: 1,

  sortKeys: ['start:desc'],
  sortedModel: computed.sort('model', 'sortKeys'),
  selectedId: null,

  tagFilterChanged: observer('tagList.tags', 'tagList.tags.[]', function() {
    this.set("tag", this.tagList.tags.join(";"));
  }),

  tagQueryParamChanged: observer("tag", function() {
    this.tagList.setTags(this.tag);
  }),

  tagsCount: computed.reads('tagList.tags.length'),

  pagedContent: computed.alias('model'),

  totalPages: computed.oneWay("pagedContent.totalPages"),

  actions: {
    beamSelection: function(beamId) {
      this.transitionToRoute("beams.beam", beamId);
    },
    addToTagList: function(tag) {
      if (tag.trim() === ''){
        return;
      }
      this.tagList.addTag(tag);
      this.set('tagName', '');
    },
    removeFromTagList: function(tag){
      this.tagList.removeTag(tag);
    },
    emptyTagList: function(){
      this.tagList.emptyTagList();
    },
  }
});
