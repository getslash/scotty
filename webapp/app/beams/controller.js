import Controller from '@ember/controller';
import { observer, computed } from '@ember/object';
import { BeamFilter } from '../utils/beam_filter';
import pagedArray from 'ember-cli-pagination/computed/paged-array';
import { alias } from '@ember/object/computed';

export default Controller.extend({
  tag: "",
  email: null,
  uid: null,
  tagList: BeamFilter.create(),
  queryParams: ['tag', 'email', 'uid', 'page'],
  page: 1,
  perPage: 15,
  

  sortKeys: ['start:desc'],
  sortedModel: computed.sort('model', 'sortKeys'),
  selectedId: null,

  tagFilterChanged: observer('tagList.tags', 'tagList.tags.[]', function() {
    this.set("tag", this.tagList.tags.join(";"));
  }),

  tagQueryParamChanged: observer("tag", function() {
    this.tagList.setTags(this.tag);
  }),

  tagsCount: computed('tagList.tags.length', function() {
    return this.get('tagList.tags.length');
  }),

  pagedContent: pagedArray('sortedModel', {
    page: alias("parent.page"),
    perPage: alias("parent.perPage")
  }),

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
