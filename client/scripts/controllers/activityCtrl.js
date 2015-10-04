var app = angular.module('app');

app.controller('activityCtrl', function($scope, mainFactory, $window, $state) {

  $scope.init = function() {
    $scope.sidenavList = [{
      name: "Add",
      data_state: "activity.add",
      data_icon: "glyphicon glyphicon-plus"
    },
    {
      name: "View",
      data_state: "activity.view",
      data_icon: "glyphicon glyphicon-eye-open"
    },
    {
      name: "Update",
      data_state: "activity.update",
      data_icon: "glyphicon glyphicon-pencil"
    }];
    $scope.state = $scope.sidenavList[0];
    $state.transitionTo($scope.state["data_state"]);

    $scope.isCollapsed = true;
  };

  $scope.isActive = function(item) {
    return item === $scope.state;
  };

  $scope.changeState = function(item) {
    $scope.state = item;
    $state.transitionTo($scope.state["data_state"]);
  };

  mainFactory.getAllStaff(function(result){
    $scope.staffs = result;
  });

  mainFactory.getAllActivity(function(result){
    $scope.activities = result;
  });


  mainFactory.getAllCategory(function(result){
    $scope.activity_category = result;
  });

  mainFactory.getAllLocation(function(result){
    $scope.activity_location = result;
  });

  $scope.addActivity = function(newactivity) {
    mainFactory.addActivity(newactivity, function(result) {
      $window.location.reload();
    });
  };

});
