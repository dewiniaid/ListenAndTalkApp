angular.module('app').controller('loginCtrl', ['$scope', '$http', 'auth', 'store', '$location', 'mainFactory',
function ($scope, $http, auth, store, $location, mainFactory) {
  $scope.login = function () {
    auth.signin({}, function (profile, token) {
      // profile.email
      mainFactory.getTeacherByEmail("staff1@example.com", function(result){
          if(!result[0]) {
            auth.signout();
          }
          else {
            // Success callback
            store.set('profile', profile);
            store.set('token', token);
            $location.path('/');
          }
      });
    }, function (error) {
      console.log("There was an error logging in", error);
    });
  }
}]);
