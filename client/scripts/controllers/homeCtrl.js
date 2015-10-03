var app = angular.module('app');

app.controller('homeCtrl', function($scope, mainFactory, auth, $window) {
  console.log('test');
  $scope.auth = auth;
	console.log(auth);
  
  mainFactory.test(function(result) {
    $scope.test = result;
  });

  $scope.logout = function() {
    auth.signout();
    store.remove('profile');
    store.remove('token');
  }
  
  $scope.post = function() {
    mainFactory.test_post($scope.postData, function(result) {
      console.log(result);
    });
  }
});
