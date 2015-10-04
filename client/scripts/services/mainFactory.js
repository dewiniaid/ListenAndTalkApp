var app = angular.module('app');

app.factory('mainFactory', function ($http, Restangular, $window){
  var factory = {};

   factory.getTeachers = function(callback) {
		 Restangular.all('/api/v1/teachers/').getList()
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

  factory.addNewStudent = function(newstudent, callback) {
    Restangular.all('/api/v1/students/').post(newstudent)
      .then(function(result){
        callback(result);
      });
  }

  factory.removeStudent = function(studentid, callback) {
    Restangular.all('/api/v1/students/' + studentid).remove()
      .then(function(result){
        callback(result);
      });
  }

  // Staff

  factory.getAllStaff = function(callback) {
    Restangular.all('/api/v1/teachers/').getList()
      .then(function(result){
        callback(result);
      });
  }

  factory.addNewStaff = function(newstaff, callback) {
    Restangular.all('/api/v1/teachers/').post(newstaff)
      .then(function(result){
        callback(result);
      });
  }

  factory.removeStaff = function(staffid, callback) {
    Restangular.all('/api/v1/teachers/' + staffid).remove()
      .then(function(result){
        callback(result);
      });
  }

  // Category
  factory.getAllCategory = function(callback) {
    Restangular.all('/api/v1/categories/').getList()
      .then(function(result){
        callback(result);
      });
  }

  // Location
  factory.getAllLocation = function(callback) {
    Restangular.all('/api/v1/locations/').getList()
      .then(function(result){
        callback(result);
      });
  }

  //
  factory.getAllActivity = function(callback) {
    Restangular.all('/api/v1/detailactivity/').getList()
      .then(function(result){
        callback(result);
      });
  }

  factory.addActivity = function(newActivity, callback) {
    Restangular.all('/api/v1/activity/').post(newActivity)
      .then(function(result){
        callback(result);
      });
  }

  //Include date
  factory.searchHistoryByStudentAndDate = function(studentId, date, callback) {
    Restangular.all('/api/v1/students/'+ studentId +'/activities').getList()
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
    console.log(students);
    Restangular.all('/api/v1/students/activity').post(students)
    .then(function(result){
      callback(result);
    });
  };

  factory.getActivityById = function(id, callback) {
    Restangular.all('/api/v1/activity/'+ id).getList()
      .then(function(result){
        callback(result);
      });
  }


  return factory;
});
