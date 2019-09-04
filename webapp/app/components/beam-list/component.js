import Component from '@ember/component';
import service from "ember-service/inject";
import getOwner from "ember-owner/get";

export default Component.extend({
  routing: service("-routing"),
  
  actions: {
    beamClick: function(beamId) {
      this.get("onSelection")(beamId);
    },
    paramsChange: function(blah){
      let currmodel = this.attrs.page;
      let query_params = { 
        page: currmodel.value,
        per_page: 9
       };
      console.log(currmodel.value);
      
      let res = blah.model.store.query('beam', query_params);
      
      const currentRouteName = this.get("routing.currentRouteName");
      const currentRouteInstance = getOwner(this).lookup(`route:${currentRouteName}`);
      currentRouteInstance.refresh();
      console.log(currentRouteName);
      console.log(currentRouteInstance);    
    },
  }
});
