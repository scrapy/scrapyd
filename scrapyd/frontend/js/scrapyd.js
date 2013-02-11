/*
Scrapyd Javascript
*/

var app = angular.module('app', ['ngResource']);

var AppCtrl = function($scope, $http) {
  
  $scope.refresh = function() {
    $http.get('/status.json')
      .success(function(data) {
      $scope.projects = data.projects;
    });
  };
  
  $scope.refresh();
}

app.controller('AppCtrl', AppCtrl);
