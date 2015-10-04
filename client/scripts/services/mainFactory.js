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
    Restangular.all('api/v1/activity').getList()
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


  factory.searchByActivityAndDate = function(activityId, date, callback) {
    Restangular.all('/api/v1/students/activity').getList({"activityId": activityId, "date": date})
      .then(function(result){
        callback(result);
      });
  }


  factory.checkIn = function(activity_id, studentsToCheckIn, date, callback) {
    var students = {"data": []};
    // package data to be sent over to controller
    for (key in studentsToCheckIn) {
      students["data"].push({"STUDENT_ID": key, "STATUS_ID": studentsToCheckIn[key]["status"], "COMMENT": studentsToCheckIn[key]["comment"], "ACTIVITY_ID": activity_id, "DATE": date})
    }
    Restangular.all('/api/v1/students/activity').post(students)
    .then(function(result){
      callback(result);
    });
  };


  return factory;
});
