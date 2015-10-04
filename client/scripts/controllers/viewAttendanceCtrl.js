var app = angular.module('app');

app.controller('viewAttendanceCtrl', function($scope, mainFactory, store, $window, $state) {
  $scope.show = {
    date: false,
    student: false
  }
  $scope.report = {}

/*  mainFactory.test(function(result) {
    $scope.test = result;
  });
*/
/*  $scope.post = function() {
    mainFactory.test_post($scope.postData, function(result) {
      console.log(result);
    });
  } */

  $scope.getSingleDateReport = function() {
    $scope.show.student = false;
    var date = $scope.report.date.toISOString().slice(0,10) + "T00:00:00Z";
    mainFactory.getAllStudentsByDate(date, function(history) {
      $scope.history = history;
    });
  }
  $scope.getSingleStudentReport = function() {
    $scope.show.date = false;
    mainFactory.getAllStudents(function(data) {
      $scope.students = data;
    });
  }
  $scope.getReport = function(studentID) {
  if (studentID) {
      mainFactory.searchHistoryByStudent(studentID, function(history){
        $scope.history = history;
        console.log($scope.history);
      });
    }
  }

  $scope.friends = [{name:'John', phone:'555-1276'},
                     {name:'Mary', phone:'800-BIG-MARY'},
                     {name:'Mike', phone:'555-4321'},
                     {name:'Adam', phone:'555-5678'},
                     {name:'Julie', phone:'555-8765'},
                     {name:'Juliette', phone:'555-5678'}];
});
