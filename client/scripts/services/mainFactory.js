var app = angular.module('app');

app.factory('mainFactory', function ($http, Restangular, $window){
  var factory = {};

  factory.test = function(callback) {
    Restangular.one('api', 'test').get()
      .then(function(result){
        callback(result);
      });
  };

  factory.test_post = function(postData, callback) {
    Restangular.all('api/test_post').post(postData)
      .then(function(result){
        callback(result);
      });
  };

  return factory;
});
