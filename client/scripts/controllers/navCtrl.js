var app = angular.module('app');

app.controller('navCtrl', function($scope, $location){
    $scope.init = function(){
      $scope.navList = [
        {name: "Activity", href: "#/activity"},
        {name: "Add New Staff", href: "#/newstaff"},
        {name: "Add New Student", href: "#/newstudent"},
        {name: "Mark Attendance", href: "#/markAttendance"},
        {name: "View Attendance", href: "#/viewAttendance"},
        {name: "Settings", href: "#/settings"}
      ];
    };
});
