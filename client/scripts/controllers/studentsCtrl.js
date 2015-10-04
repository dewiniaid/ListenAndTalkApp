var app = angular.module('app');

app.controller('studentsCtrl', function($scope, mainFactory, $window, $state) {

  mainFactory.getAllStudents(function(result) {
    $scope.students = result;
  });


});
