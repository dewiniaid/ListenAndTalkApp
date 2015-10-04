var app = angular.module('app');

app.controller('studentsCtrl', function($scope, mainFactory, $window, $state) {
  mainFactory.getAllStudents(function(result) {
    $scope.students = result;
  });

  mainFactory.getAllActivities(function(result) {
  	$scope.activities = result;
  });


  var studentsToCheckIn = {};
  $scope.checkin = function(status, studentID) {
	// studentsToCheckIn.push({"status": status, "studentID": studentID})
	studentsToCheckIn[studentID] = status;
	console.log(studentsToCheckIn);
	if (Object.keys(studentsToCheckIn).length == $scope.students.length) {
		mainFactory.checkIn(function() {
			console.log('test');
		})
	};
  }
});
