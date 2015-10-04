var app = angular.module('app');

app.controller('staffCtrl', function($scope, mainFactory, $window, $state) {
  mainFactory.getAllStaff(function(result) {
    $scope.staffs = result;
    console.log(result);
  });

  $scope.addNewStaff = function() {
    mainFactory.addNewStaff($scope.newstaff, function(result) {
      console.log(result);
      $window.location.reload();
    });
  }

  $scope.removeStaff = function(staffid) {
    mainFactory.removeStaff(staffid, function(result) {
      console.log(result);
      $window.location.reload();
    });
  }

});
