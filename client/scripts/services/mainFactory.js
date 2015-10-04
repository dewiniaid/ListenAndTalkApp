var app = angular.module('app');

app.factory('mainFactory', function($http, Restangular, $window){
  var factory = {};

  factory.test = function(callback) {
    // /api/test
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

  // Student
  factory.getAllStudents = function(callback) {
    Restangular.all('api/v1/students').getList()
      .then(function(result){
        callback(result);
      });
  };


  return factory;
});
