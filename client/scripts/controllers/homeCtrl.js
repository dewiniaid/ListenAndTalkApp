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
  
  //auth.profile.email
  mainFactory.getActivityByTeacherEmail("staff1@example.com", function(result) {
    $scope.activityNames = result;
  });
    
     mainFactory.getAllStudents(function(result) {
    $scope.students = result;
         console.log(result);
  });
  
});
