import TextField from '@ember/component/text-field';

export default TextField.extend({
  didInsertElement() {
    this.$().focus();
  }
});
