import Route from '@ember/routing/route';
import { task, timeout } from 'ember-concurrency';
import RouteMixin from 'ember-cli-pagination/remote/route-mixin';

export default Route.extend(RouteMixin, { 
  queryParams: {
    tag: {refreshModel: true},
    email: {refreshModel: true},
    uid: {refreshModel: true},
    page: {refreshModel: false}
  },
  perPage: 5,

  periodicRefresh: task(function * () {
    for (;;) {
      yield timeout(1000 * 60 * 5);
      this.refresh();
    }
  }).on("activate").cancelOn('deactivate').drop(),

  model: function(params) {
    let query_params = { page: params.page };

    if (params.tag) {
      query_params.tag = params.tag;
    } else if (params.email) {
      query_params.email = params.email;
    } else if (params.uid) {
      query_params.uid = params.uid;
    }
    // query_params.paramMapping = {page: "page"};

    // let beams = this.store.query("beam", query_params);
    let beams =  this.findPaged('beam', query_params);
    console.log(beams);
    return beams;

    // return Ember.RSVP.hash({
    //   beams: this.findPaged('beam', queryParams)
    // });
  },

  afterModel(model) {
    return model.get('meta');
  },

  actions: {
    beamSelected: function(beam) {
      this.controllerFor("beams").set("selectedId", beam);
    }
  }
});
