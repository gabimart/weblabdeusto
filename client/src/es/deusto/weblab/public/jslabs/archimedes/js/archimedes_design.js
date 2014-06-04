//! This script is meant to contain the logic of the design view, to be used with the Composer.
//!

ArchimedesDesign = new function() {

    //! Activates the Design View.
    //!
    this.enableDesignView = function() {

        // Show everything.
        View = {};
        archimedesExperiment.updateView(View);

        // Hide the timer, show the EDIT MODE notice.
        $("#editmodeh").removeClass("hide");
        $("#timer").hide();

        // Add makerts to the editable field and turn off the standard event handlers.
        $(".arch-control, .arch-img-wrapper, .arch-camera").toggleClass("design-editable");
        $("td:first-child").toggleClass("design-editable").toggleClass("design-editable-marked");

        $(".arch-control, .arch-img-wrapper, .arch-camera").off("click");
        $(".arch-img-wrapper, .arch-camera").off("mouseenter mouseleave");

        $(".arch-control, .arch-img-wrapper, .arch-camera, td:first-child").click(function(){
           $(this).toggleClass("design-disabled");
        });

        // TODO: Enable or disable up/down controls together.
    };


    //! Gets the View definition that matches the user's selection.
    //!
    this.getView = function() {
        var instances = archimedesExperiment.instances;
        var view = {};

        $.each(instances, function(name, inst) {
            console.log(name);
            v = [];
            if(!inst.elements["webcam"].hasClass("design-disabled"))
                v.push("webcam");
            if(!inst.elements["controls"].hasClass("design-disabled"))
                v.push("controls");
            if(!inst.elements["hdcam"].hasClass("design-disabled"))
                v.push("hdcam");
            if(!inst.elements["plot"].hasClass("design-disabled"))
                v.push("plot");

            var tsensors = $("#" + name + "-" + "table-sensors");
            var tliquid = $("#" + name + "-" + "table-liquid");
            var tball = $("#" + name + "-" + "table-ball");

            if(!tsensors.datatable("getElement", "liquid.level").prev().hasClass("design-disabled"))
                v.push("sensor_level");
            if(!tsensors.datatable("getElement", "ball.weight").prev().hasClass("design-disabled"))
                v.push("sensor_weight");

            if(!tliquid.datatable("getElement", "density").prev().hasClass("design-disabled"))
                v.push("liquid_density");
            if(!tliquid.datatable("getElement", "internal.diameter").prev().hasClass("design-disabled"))
                v.push("liquid_diameter");

            if(!tball.datatable("getElement", "mass").prev().hasClass("design-disabled"))
                v.push("ball_mass");
            if(!tball.datatable("getElement", "diameter").prev().hasClass("design-disabled"))
                v.push("ball_diameter");
            if(!tball.datatable("getElement", "density").prev().hasClass("design-disabled"))
                v.push("ball_density");
            if(!tball.datatable("getElement", "volume").prev().hasClass("design-disabled"))
                v.push("ball_volume");

//        "default" : ["controls", "sensor_weight", "sensor_level",  "webcam", "hdcam", "plot", "ball_mass",
//        "ball_volume", "ball_diameter", "ball_density", "liquid_density", "liquid_diameter"]

            view[name] = v;
        });

        return view;
    };


};

