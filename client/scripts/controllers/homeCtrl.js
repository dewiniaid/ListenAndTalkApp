var app = angular.module('app');

app.controller('homeCtrl', function($scope, auth) {
	$scope.auth = auth;
	console.log('test');
	console.log(auth);
});
