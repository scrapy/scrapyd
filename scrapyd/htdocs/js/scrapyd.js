/*
Scrapyd Javascript
*/

var app = angular.module('app', ['ngResource']);

app.config(function($interpolateProvider) {
  $interpolateProvider.startSymbol('[[');
  $interpolateProvider.endSymbol(']]');
});


var AppCtrl = function($scope, $http) {

  $http.get('/status.json')
    .success(function(data) {
    $scope.projects = data.projects;
  });

  $http.get('/listspiders.json?project=*')
    .success(function(data) {
    $scope.spiders = data.spiders;
  });
  
  $scope.refresh = function() {
    $http.get('/d')
      .success(function(data) {
      $scope.tasks = data;
    });
  };
  
  $scope.refresh();
}

app.controller('AppCtrl', AppCtrl);
