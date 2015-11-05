import FilteredBeams from '../filtered-beams';

export default FilteredBeams.extend({
  model: function(params) {
    return this.store.query("beam", {
      uid: params.uid
    });
  },
  what: "user"

});
