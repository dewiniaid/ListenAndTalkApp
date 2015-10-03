var app = angular.module('app');

app.factory('mainFactory', function($http, Restangular, $window){
  var factory = {};

  factory.test = function(callback) {
    Restangular.one('api', 'test').get()
      .then(function(result){
        callback(result);
      });
  }

  return factory;
});
