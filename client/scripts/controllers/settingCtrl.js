var app = angular.module('app');

app.controller('settingCtrl', function($scope, mainFactory, store, $window, $state) {

	mainFactory.getTeachers(function(result) {
		$scope.teachers = result;
	});

	mainFactory.getAllStudents(function(result) {
		$scope.students = result;
	});

	
//	var teacherDeactivateList = {};
//	$scope.deactivate = function(status, teacherID);
//	teacherDeactivateList.push(status, teacherID);
//	console.log(teacherDeactivateList);
//	
//	}

});
