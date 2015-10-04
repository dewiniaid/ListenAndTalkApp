var app = angular.module('app');

app.controller('studentsCtrl', function($scope, mainFactory, $window, $state) {

  mainFactory.getAllStudents(function(result) {
    $scope.students = result;
  });

  mainFactory.getAllActivities(function(result) {
  	$scope.activities = result;
  });
  
  $scope.checkin = function(status) {
	console.log(status);
	mainFactory.checkIn(function() {
		console.log('test');
	})
  }
});
