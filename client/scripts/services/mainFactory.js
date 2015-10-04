var app = angular.module('app');

app.factory('mainFactory', function ($http, Restangular, $window){
  var factory = {};

  // factory.test_post = function(postData, callback) {
  //   Restangular.all('api/test_post').post(postData)
  //     .then(function(result){
  //       callback(result);
  //     });
  // };

  // Student
  factory.getAllStudents = function(callback) {
    Restangular.all('api/v1/students').getList()
      .then(function(result){
        callback(result);
      });
  };

  factory.getAllActivities = function(callback) {
    Restangular.all('api/v1/activities').getList()
      .then(function(result){
        callback(result);
      });
  };

  // Teacher
  factory.getTeacherByEmail = function(email, callback) {
    Restangular.all('api/v1/teachers/' + email).getList()
      .then(function(result){
        callback(result);
      });
  };
    
  factory.getActivityByTeacherEmail = function(email, callback) {
    Restangular.all('api/v1/teachers/' + email + '/activity').getList()
      .then(function(result){
        callback(result);
      });
  };  

  factory.checkIn = function(callback) {
    callback();
  }


  return factory;
});
