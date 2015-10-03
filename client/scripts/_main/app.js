var app = angular.module('app', ['ui.router', 'mgcrea.ngStrap', 'ngAnimate', 'restangular']);

app.config(function($stateProvider, $urlRouterProvider){
  $stateProvider
  .state('home',{
    url: '/',
    controller: 'homeCtrl',
    templateUrl: 'partials/home.html'
  })
  .state('test', {
    url: '/test',
    controller: 'homeCtrl',
    templateUrl: 'partials/test.html'
  })
  .state('about', {
    url: '/about',
    templateUrl: 'partials/about.html'
  });

  $urlRouterProvider.otherwise('/');

});
