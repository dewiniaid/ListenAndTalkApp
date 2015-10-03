var app = angular.module('app');

app.controller('homeCtrl', function($scope, mainFactory) {
  mainFactory.test(function(result) {
    $scope.test = result;
  });
});
