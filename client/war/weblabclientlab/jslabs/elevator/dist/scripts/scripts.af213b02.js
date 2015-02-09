(function(){"use strict";angular.module("elevatorApp",["ngAnimate","ngResource","ngRoute","ngSanitize","ngTouch","angularFileUpload"]).config(["$routeProvider",function(a){return a.when("/",{templateUrl:"views/main.html",controller:"MainCtrl"}).when("/about",{templateUrl:"views/about.html",controller:"AboutCtrl"}).otherwise({redirectTo:"/"})}])}).call(this),function(){"use strict";angular.module("elevatorApp").controller("MainCtrl",["$scope",function(a){return a.clickButton=function(a){return console.debug("Clicked button: "+a)},a.awesomeThings=["HTML5 Boilerplate","AngularJS","Karma"]}])}.call(this),function(){"use strict";angular.module("elevatorApp").controller("AboutCtrl",["$scope",function(a){return a.awesomeThings=["HTML5 Boilerplate","AngularJS","Karma"]}])}.call(this),function(){"use strict";angular.module("elevatorApp").directive("wlWebcam",["$timeout",function(a){return{templateUrl:"views/wlwebcam.html",restrict:"E",scope:{src:"@src"},link:function(b,c){return c.find("img").bind("load error",function(){return b.refreshSoon()}),b.refreshSoon=function(){return a(function(){b.doRefresh()},1e3)},b.doRefresh=function(){var a;return a=URI(b.src),a.query({rnd:1e5*Math.random()}),b.src=a.toString()}}}}])}.call(this),function(){"use strict";angular.module("elevatorApp").directive("wlbutton",function(){return{templateUrl:"views/wlbutton.html",scope:{ident:"@ident"},restrict:"E",link:function(){}}})}.call(this),function(){"use strict";angular.module("elevatorApp").directive("wlUpload",["$upload",function(a){return{templateUrl:"views/wlupload.html",restrict:"E",link:function(b){return b.$watch("files",function(){return void 0!==b.files?(console.log("WATCH HAS: "),console.log(b.files),b.upload=a.upload({url:"../../../web/upload/",data:{},file:b.files}).progress(function(a){return console.log("Progress: "+parseInt(100*a.loaded/a.total)+"% file : "+a.config.file.name)}).success(function(a,b,c,d){return console.log("file "+d.file.name+"is uploaded successfully. Response: "+a)}).error(function(){return console.error("Could not upload the file")})):void 0})}}}])}.call(this);