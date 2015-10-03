var app = angular.module('app');

app.controller('homeCtrl', function($scope, mainFactory, auth) {
	console.log('test');
  $scope.auth = auth;
	console.log(auth);
  mainFactory.test(function(result) {
    $scope.test = result;
  });
});
