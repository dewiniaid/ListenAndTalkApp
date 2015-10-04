angular.module('app').controller('loginCtrl', ['$scope', '$http', 'auth', 'store', '$location', 'mainFactory',
function ($scope, $http, auth, store, $location, mainFactory) {
  $scope.error = "";
  $scope.login = function () {
    $scope.error = "";
    auth.signin({}, function (profile, token) {
      // Pass profile.email instead of "staff1@example.com" to make sure only staff can access
      mainFactory.getTeacherByEmail(profile.email, function(result){
      // mainFactory.getTeacherByEmail("staff1@example.com", function(result){
          // Staff not Found.
          if(!result[0]) {
            auth.signout();
            $scope.error = "ID not found.";
          }
          else {
            // Success callback
            store.set('profile', profile);
            store.set('token', token);
            $location.path('/');
          }
      });
    }, function (error) {
      $scope.error = error;
    });
  }
}]);
