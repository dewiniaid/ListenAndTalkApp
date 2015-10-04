var app = angular.module('app');

app.controller('homeCtrl', function($scope, mainFactory, auth, store, $window, $state) {
  $scope.auth = auth;

  $scope.logout = function() {
    auth.signout();
    store.remove('profile');
    store.remove('token');
    $window.location.reload();
  }

  // $scope.post = function() {
  //   mainFactory.test_post($scope.postData, function(result) {
  //     console.log(result);
  //   });
  // }
});
