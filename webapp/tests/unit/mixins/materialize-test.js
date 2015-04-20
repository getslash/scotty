import Ember from 'ember';
import MaterializeMixin from '../../../mixins/materialize';
import { module, test } from 'qunit';

module('MaterializeMixin');

// Replace this with your real tests.
test('it works', function(assert) {
  var MaterializeObject = Ember.Object.extend(MaterializeMixin);
  var subject = MaterializeObject.create();
  assert.ok(subject);
});
