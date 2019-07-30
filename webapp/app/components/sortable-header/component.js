import Component from '@ember/component';

export default Component.extend({
    tagName: 'th',  

    actions: {
        sortBy(sortProperty, acsending) {
            this.sortBy(sortProperty, acsending);
        }
    }
});
