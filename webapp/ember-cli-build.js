/* global require, module */
var EmberApp = require('ember-cli/lib/broccoli/ember-app');

module.exports = function(defaults) {
  var app = new EmberApp({
    'ember-cli-bootstrap-sassy': {
      'quiet': true
    },
    babel: {
      includePolyfill: true
    },
    vendorFiles: {
      'handlebars.js': null
    }});

  // Use `app.import` to add additional libraries to the generated
  // output files.
  //
  // If you need to use different assets in different
  // environments, specify an object as the first parameter. That
  // object's keys should be the environment name and the values
  // should be the asset to use in that environment.
  //
  // If the library that you are including contains AMD or ES6
  // modules that you would like to import into your application
  // please specify an object with the list of modules as keys
  // along with the exports of each module as its value.
  app.import('bower_components/fontawesome/css/font-awesome.min.css');

  app.import("bower_components/moment/moment.js");
  app.import("bower_components/numeral/numeral.js");
  app.import("bower_components/materialize/dist/js/materialize.min.js");

  var mergeTrees = require('broccoli-merge-trees');
  var pickFiles = require('broccoli-static-compiler');

  var fontTree = pickFiles('bower_components/fontawesome/fonts', {
    srcDir: '/',
    files: ['fontawesome-webfont.eot','fontawesome-webfont.ttf','fontawesome-webfont.svg','fontawesome-webfont.woff'],
    destDir: '/fonts'
  });

  var robotoTree = pickFiles('bower_components/materialize/font', {
    srcDir: '/',
    destDir: '/font'
  });

  return mergeTrees([app.toTree(), fontTree, robotoTree], {overwrite: true});
};
