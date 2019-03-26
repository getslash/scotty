import Controller from '@ember/controller';
import {BeamFilter} from '../../utils/beam_filter'

export default Controller.extend({
    init(){
        this._super(...arguments);
        this.set('tagList', BeamFilter.create());
    }
}); 