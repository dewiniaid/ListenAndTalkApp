var app = angular.module('app');

app.controller('settingCtrl', function($scope, mainFactory, store, $window, $state) {

	
mainFactory.getTeachers(function(result) {
		$scope.teachers = result;
		console.log($scope.teachers);
	});
	
	mainFactory.getAllStudents(function(result) {
		$scope.students = result;
	});
	
	mainFactory.dectivateTeacherQuery(function() {
		
	});
//	$scope.deactivate(teachers.id, )

	
//	$scope.deactivate = function(status, teacherID);
//	teacherDeactivateList.push(status, teacherID);
//	console.log(teacherDeactivateList);
//	
//	}

});
