import FilteredBeams from './filtered-beams';

export default FilteredBeams.extend({
  model: function(params) {
    return this.store.query("beam", {
      tag: params.tag
    });
  },
  what: "tag"
});
