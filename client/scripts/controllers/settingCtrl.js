var app = angular.module('app');

app.controller('settingCtrl', function($scope, mainFactory, store, $window, $state) {

	mainFactory.getTeachers(function(result) {
		$scope.students = result;
	});


//	var studentsToCheckIn = {};
//	$scope.checkin = function(status, studentID) {
//		// studentsToCheckIn.push({"status": status, "studentID": studentID})
//		studentsToCheckIn[studentID] = status;
//		console.log(studentsToCheckIn);
//		if (Object.keys(studentsToCheckIn).length == $scope.students.length) {
//			mainFactory.checkIn(function() {
//				console.log('test');
//			})
//		};
//	}
});
