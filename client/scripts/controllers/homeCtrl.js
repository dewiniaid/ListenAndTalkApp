var app = angular.module('app');

app.controller('homeCtrl', function($scope, mainFactory, $window) {
  mainFactory.test(function(result) {
    $scope.test = result;
  });

  $scope.post = function() {
    mainFactory.test_post($scope.postData, function(result) {
      console.log(result);
    });
  }
});
