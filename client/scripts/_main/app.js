var app = angular.module('app', ['ui.router', 'mgcrea.ngStrap', 'ngAnimate', 'auth0', 'angular-storage', 'angular-jwt']);

app.config(function($stateProvider, $urlRouterProvider){
  $stateProvider
  .state('home',{
    url: '/',
    templateUrl: 'partials/home.html'
  })
  .state('about', {
    url: '/about',
    templateUrl: 'partials/about.html'
  });

  $urlRouterProvider.otherwise('/');

});
