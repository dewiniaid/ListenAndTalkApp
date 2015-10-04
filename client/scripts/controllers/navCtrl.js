var app = angular.module('app');

app.controller('navCtrl', function($scope, $location){
    $scope.init = function(){
      $scope.navList = [
        {name: "Test", href: "#/test"},
        {name: "Mark Attendance", href: "#/markAttendance"},
        {name: "View Attendance", href: "#/viewAttendance"},
        {name: "Settings", href: "#/settings"}
      ];
    };
});
