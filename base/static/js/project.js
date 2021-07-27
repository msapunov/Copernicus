var DATES = ["January", "April", "September"];
var EXAM_MTH = "January";
var EXAM_DAY = 15;

function date_warning(){
    moment.locale("en");

    for (i in DATES){
        var month = DATES[i];
        var day = moment().month(month).daysInMonth();
        var end = moment().month(month).date(day);
        if(moment().isSameOrBefore(end)){
            break;
        }
    }
    var end_date = end.format("Do of MMMM");
    var exam_date = end.add(EXAM_DAY, "days").format("Do of MMMM YYYY");
    return "Request submitted before the {0} will be examined the {1}.".f(end_date, exam_date);
}

function end_warning(){
    var start = moment().month(1).date(15).format(); // First session in February
    var end = moment().month(9).date(30).format(); // Last session in Septembre
    var between = moment().isBetween(start, end);
    var prefix = (between) ? "Additional" : "Allocated";
    var year = moment().add(1, "years").format("YYYY");
    return prefix + " resources must be used before the end of February {0}.".f(year);
}

function reduce_to_names(initial, object){
    if(initial.length > 0){
        return initial + ", " + object.text;
    }else{
        return object.text;
    }
}


(function(window, document, $, undefined){
    "use strict";
    Dropzone.autoDiscover = false;
    window.contact = "mesocentre-techn@univ-amu.fr";
    window.proj = {};
    window.proj.url = {
        add: "project/add/user",
        assign: "project/assign/user",
        new_resp: "project/assign/responsible",
        user_list: "user/list",
        extend: "project/extend",
        renew: "project/renew",
        delete: "project/delete/user",
        history: "project/history",
        activate: "project/reactivate",
        transform: "project/transform",
        activity: "project/activity",
        activity_upload: "project/activity/upload",
        activity_clean: "project/activity/clean",
        activity_delete: "project/activity/remove",
        modal_allocate: "/project/modal/allocate",
        modal_transform: "/project/modal/transform",
        modal_activate: "/project/modal/activate",
        modal_assign: "/project/modal/attach/user"
    };

    window.error = function(req){
        var text = $.trim(req.responseText);
        var status = $.trim(req.status);
        var statText = $.trim(req.statusText);
        if((text) && (text.length > 0)){
            var msg = "Status code: {0}\nMessage: {1}\n".f(status, text);
        }else{
            var msg = "Server return {0}: {1}\n".f(status, statText);
        }
        msg += "Please contact technical team: {0}".f(window.contact);
        alert(msg);
    };

    window.render = {};

    window.render.window_hide = function(e){
        var name = $.trim( $(this).data("modal") );
        var modal = UIkit.modal("#" + name);
        if ( modal.isActive() ) {
            modal.hide();
        }
    };

    window.render.window_visibility_control = function(e){
        var name = $.trim( $(this).data("modal") );
        var modal = UIkit.modal("#" + name);
        if ( modal.isActive() ) {
            modal.hide();
        } else {
            modal.show();
        }
    };

    window.render.input_empty = function(){
        $(this).val().length < 1 ? $(this).addClass("uk-form-danger") : $(this).removeClass("uk-form-danger");
    };

    window.render.check_positive = function(is_num, message){
        var msg = "{0} must be a positive number".f(message);
        if(!/^\d+$/.test(is_num)){
            alert(msg);
            return false;
        }
        return true;
    };

    window.render.paint_red = function(data){
        var regex = new RegExp("^[\\s\\0\\n\\r\\t\\v]+$");
        var result = true;
        $.each(data, function(key, value){
            if( (!value) || (value.length < 1) || (regex.test(value)) ){
                $("[name={0}]".f(key)).addClass("uk-form-danger");
                result = false;
            }
        });
        return result
    };

    window.render.new_user = function(e){
            var modal = $.trim( $(this).data("modal") );
            var form = $.trim( $(this).data("form") );
            $.ajax({
                data: $("#" + form).serialize(), // serializes the form's elements.
                timeout: 60000,
                type: "POST",
                url: window.proj.url.add
            }).done(function(reply){
                if (reply.message) {
                    UIkit.notify(reply.message, {
                        timeout: 3000,
                        status: "success"
                    });
                }
                UIkit.modal("#" + modal).hide();
            }).fail(function(reply){
                show_error(reply);
            });
            e.preventDefault();
    };

    window.render.extend = function(e){
        var modal = $.trim( $(this).data("modal") );
        var form = $.trim( $(this).data("form") );
        $.ajax({
            data: $("#" + form).serialize(), // serializes the form's elements.
            timeout: 60000,
            type: "POST",
            url: window.proj.url.extend
        }).done(function(reply){
            if (reply.message) {
                UIkit.notify(reply.message, {
                    timeout: 3000,
                    status: "success"
                });
            }
            UIkit.modal("#" + modal).hide();
        }).fail(function(reply){
            show_error(reply);
        });
        e.preventDefault();
    };
    /*
    window.render.extend = function(name, id, renew){
        var title, url;
        if(renew){
            title = "Request to renew CPU hours for the project {0}?".f(name);
        }else {
            title = "Request additional CPU hours for the project {0}?".f(name);
        }
        var placeholder = "Motivation:\nShort description of the request";
        var cpu = $("<input/>").addClass("uk-width-1-1").attr({
            "id": name+"_cpu",
            "name": "cpu",
            "type": "text",
            "placeholder": "CPU hours"
        });
        var motiv = $("<textarea/>").addClass("uk-width-1-1").attr({
            "id": name + "_motivation",
            "rows": "4",
            "name": "note",
            "placeholder": placeholder
        });
        var checkbox = $("<input>").attr({
            "id": "exception_checkbox",
            "name": "exception",
            "type": "checkbox"
        }).addClass("uk-margin-small-right uk-form-danger");
        var label = $("<label/>").attr('for', "exception_checkbox");
        label.text("Select this checkbox only in case you would need an exceptional extension! Will only be considered for a project running out of CPU time way before the next application deadline (see the date above).");
        //label.text("Select checkbox for an exceptional extension request only! Apply for a project running out of CPU time way before the next session.");
        var express = $("<div/>").addClass(
            "uk-form-row uk-alert uk-alert-danger"
        );
        express.append(checkbox).append(label);
        var warn = "<div>" + date_warning() + "</div><div>" + end_warning() + "</div>";
        var form = $("<form/>").addClass("uk-form");
        form.append($("<legend/>").text(title));
        form.append($("<div>{0}</div>".f(warn)).addClass("uk-form-row uk-alert"));
        if(!renew){
            form.append(express);
        }
        form.append($("<div/>").addClass("uk-form-row").append(cpu));
        form.append($("<div/>").addClass("uk-form-row").append(motiv));


        var report = $("<div>{0}</div>".f("Make sure that you have uploaded project activity report first!")).addClass("uk-form-row uk-alert uk-alert-warning");
        if(renew) {
            form.append(report);
        }
        if(renew){
            url = window.proj.url["renew"];
        }else{
            url = window.proj.url["extend"]
        }
        var pop = dialog(form.prop("outerHTML"), function(){
            var exception = $("#exception_checkbox").is(':checked') ? "yes" : "no";
            var cid = name+"_cpu";
            var cpu_id = "#" + name+"_cpu";
            var tt = $(form).find(cpu_id).val();
            var xxx = $(form);
            var ppp = xxx.serialize();
            var kkk = xxx.serializeArray();
            var pp = document.getElementById(name+"_cpu").value;
            var data = {
                "cpu": $("#" + name+"_cpu").val(),
                "note": $("#" + name+"_motivation").val(),
                "exception": exception,
                "project": id
            };
            if(!window.render.paint_red(data)){
                return false;
            }
            if(!window.render.check_positive(data["cpu"], "CPU hours")){
                return false;
            }
            json_send(url, data).done(function(reply){
                if(reply.message){
                    UIkit.notify(reply.message, {timeout: 2000, status:"success"});
                }
                pop.hide();
            });
        });
    };
    */

    window.render.transform = function(e){
        var name = $.trim( $(this).data("name") );
        $.ajax({
            data: $("#" + name + "_transformation_form").serialize(), // serializes the form's elements.
            timeout: 60000,
            type: "POST",
            url: window.proj.url.transform
        }).done(function(reply){
            if (reply.message) {
                UIkit.notify(reply.message, {
                    timeout: 3000,
                    status: "success"
                });
            }
            window.render.window_visibility_control(e);
        }).fail(function(reply){
            show_error(reply);
        });
        e.preventDefault();
    };

    window.render.remove_user = function(e){
        var id = $(this).data("pid");
        var full = $(this).data("name");
        var login = $(this).data("login");
        var name = $(this).data("project");
        var txt = "Are you sure you want to remove {0} from the project {1}?".f(full, name);
        var data = {"project": id, "login": login};
        UIkit.modal.confirm(txt, function(){
            json_send(window.proj.url["delete"], data).done(function(reply){
                var uid = "{0}_{1}".f(name, login);
                var btn = $("#"+uid).find("button").css("visibility", "hidden");
                $("#"+uid).find(".uk-margin-small-left").addClass("uk-text-muted");
            });
        });
    };

    window.render.assign_responsible = function(e){
        var name = $(this).data("name");
        var id = $(this).data("project");
        var list_id = "#"+id+"_assign_list";

        var div = $(list_id).clone();
        var rnd = list_id.hashCode();
        dialog(div.addClass(rnd).show().prop("outerHTML"), function(){
            var select = $("."+rnd).children(".admin_assign_select");
            if(select.length < 1){
                return true;
            }
            var full = $(select).find(":selected").text();

            var data = {
                "login": select.val(),
                "project": id
            };
            var text = "You are about to assign {0} as the responsible person for the project {1}. Are you sure?".f(full, name);
            window.render.user_confirmation(window.proj.url.new_resp, data, text, {"name": name, "id": id});
            return true;
        });
    };

    window.render.user_confirmation = function(url, data, text, p_object){
        var div = $("<h3/>").text(text);
        var pop = dialog(div.prop("outerHTML"), function(){
            json_send(url, data).done(function(reply){
                if(reply.message){
                    UIkit.notify(reply.message, {timeout: 2000, status:"success"});
                }
                pop.hide();
                window.render.user_reshuffle(reply, p_object)
            });
        });
    };

    window.render.del_button = function(project, user, disable){
        var btn = $("<button/>").attr({
                "type": "button",
                "data-pid": project.id,
                "data-name": user.fullname,
                "data-login": user.login,
                "data-project": project.name
            });
        if( user.responsible || disable==true){
            btn.addClass("uk-button uk-button-mini uk-button-link uk-icon-justify");
            btn.prop("disabled",true);
        }else{
            btn.addClass("uk-button uk-button-mini uk-button-link uk-text-danger remove uk-icon-justify");
            btn.append($("<span/>").addClass("uk-icon-close"));
        }
        return btn
    };

    window.render.history = function(data, title){
        var info = $("<table/>").addClass("uk-table uk-table-striped uk-table-condensed");
        data.sort(function(a,b){
            return new Date(b.date) - new Date(a.date);
        });
        data.forEach(function(user){
            var tr = $("<tr>");
            ["date", "message"].forEach(function(attr){
                var txt = user[attr];
                txt = txt.replace(/</g, "&lt;");
                txt = txt.replace(/>/g, "&gt;");
                tr.append("<td>" + txt + "</td>");
            });
            info.append(tr);
        });

        $("#modal_body").html(info.prop("outerHTML"));

        var modal = UIkit.modal("#modal");
        if ( modal.isActive() ) {
            modal.hide();
        } else {
            modal.show();
        }
    };

    window.render.project_history = function(e){
        var name = $(this).data("name");
        var id = $(this).data("project");
        var title = "History for project {0}".f(name);
        var data = {"project": id};
        json_send(window.proj.url["history"], data).done(function(reply){
            if(reply.length > 0){
                window.render.history(reply, title);
            }else{
                UIkit.modal.alert("No history found for project {0}".f(name));
            }
        });
    };

    window.render.btn_reshuffle = function(proj, login){
        var id = "#{0}_{1}".f(proj, login);
        var prnt = $(id).parent("div");
        $(id).remove();

        var btns = prnt.find("button");
        if(btns.length == 1){
            btns[0].remove();
        }
    };

    window.render.user_reshuffle = function(reply, p_object){
        var name = p_object.name;
        var pid = p_object.id;
        var users_div = "#"+name+"_project_users";
        $(users_div).empty();
        var users = reply.data;
        users.sort(function(a,b){
            if(a.fullname < b.fullname)
                return -1;
            if(a.fullname > b.fullname)
                return 1;
            return 0;
        });
        $.each(users, function(idx, value){
            if(!value.active){
                return true;
            }
            var btn_rndr = (value.active == "Suspended");
            var btn = window.render.del_button({id: pid, name: name}, value, btn_rndr);
            var id = "{0}_{1}".f(name, value.login);
            if(value.consumption){
                var info = "{0}: {1}".f(value.fullname, value.consumption);
            }else{
                var info = "{0}".f(value.fullname);
            }
            var txt = $("<span/>").addClass("uk-margin-small-left").attr("title", value.email).text(info);
            if(btn_rndr){
                txt.addClass("uk-text-muted");
            }
            var div = $("<div/>").addClass("uk-panel").attr({"id": id}).append(
                btn
            ).append(
                txt
            );
            $(users_div).append(div);
        });
    };

    window.render.hidden_field = function(resp){
        if(!resp.data){
            alert("Server response is corrupted!");
            return false;
        }
        if((!resp.data.incoming_name)||(!resp.data.saved_name)){
            alert("Server response is incomplete!");
            return false;
        }
        var saved = resp.data.saved_name;
        for(var i of [1, 2, 3]) {
            var value = $("input[name=image_{0}]".f(i)).val();
            if(! value){
                $("input[name=image_{0}]".f(i)).val(saved);
                break
            }
        }
        return saved
    };

    window.render.clean_activity = function(project_name){
        $.post("{0}/{1}".f(window.proj.url["activity_clean"], project_name));
    };

    window.render.delete_activity = function(project, name){
        let url = "{0}/{1}/{2}".f(window.proj.url["activity_delete"], project, name);
        json_send(url).done(function(reply){
            if(reply.data === true){
                UIkit.notify("File {0} has been removed from the server".f(name), {
                    timeout: 2000,
                    status: "success"
                });
            }
        });
    };

    window.render.user_list = function(){
        $(".select2_users").select2({
            ajax: {
                delay: 250,
                url: window.proj.url.user_list,
                dataType: "json"
            },
            placeholder: "Select already registered user",
            allowClear: true,
            cache: true,
            width: 'resolve',
            language: {
                searching: function() {
                    return "Searching...";
                }
            },
            name: "users[]"
        });
    };

    window.render.shadow = function(e){
        var project = $(this)[0].id.split("_")[0];
        var select2 = $("#" + project + "_login");
        var name = $("#" + project + "_name");
        var surname = $("#" + project + "_surname");
        var mail = $("#" + project + "_email");
        var gg = $(select2).select2('data');
        var hh = $(select2).find(':selected');

        if( $(name).val().length > 0 || $(surname).val().length > 0 || $(mail).val().length > 0 ){
            $(select2).prop("disabled", true);
        }else if( $(name).val().length == 0 && $(surname).val().length == 0 && $(mail).val().length == 0 ){
            $(select2).prop("disabled", false);
        }
        if( $(select2).select2('data').length > 0 ){
            $(name).prop("disabled", true);
            $(surname).prop("disabled", true);
            $(mail).prop("disabled", true);
        }else if( $(select2).select2('data').length == 0 ){
            $(name).prop("disabled", false);
            $(surname).prop("disabled", false);
            $(mail).prop("disabled", false);
        }
    };

    window.render.modal = function(url, btn, fn){
        $.ajax({
            timeout: 60000,
            type: "POST",
            url: url,
            success: function(data){
                 $("body").append(data);
                 $("button."+btn).prop("disabled", false);
                if (typeof fn === "function") fn();
            }
        }).fail(function(request){
            show_error(request);
        });
    };

    window.render.activity = function(e){
        var name = $(this).data("name");
        window.render.clean_activity(name);
        var title = "Activity report for the project {0}".f(name);
        var report = $("<textarea/>").addClass("uk-width-1-1").attr({
            "rows": "5",
            "name": "report",
            "placeholder": "50 lines maximum"
        });
        var doi = $("<textarea/>").addClass("uk-width-1-1").attr({
            "rows": "5",
            "name": "doi",
            "placeholder": "List of publications (DOI) for last activity period"
        });
        var training = $("<textarea/>").addClass("uk-width-1-1").attr({
            "rows": "5",
            "name": "training",
            "placeholder": "List of students (licence, master, doctorat) trained recently"
        });
        var hiring = $("<textarea/>").addClass("uk-width-1-1").attr({
            "rows": "5",
            "name": "hiring",
            "placeholder": "List of people hired during last activity period"
        });
        var upload = $("<div/>").attr({"id": "upload"}).addClass("dropzone uk-alert uk-text-center").append(
            $("<div/>").addClass("dz-default dz-message").text("Drop files to upload (or click here). Total 3 images are allowed, limited by 3 Mb per image. Supported formats are jpeg, png and gif")
        );
        var form = $("<form/>").addClass("uk-form uk-accordion").attr("data-uk-accordion", "{collapse: false}").append(
            $("<legend/>").text(title)
        ).append(
            $("<h3/>").addClass("uk-accordion-title").text("Report"),
            $("<div/>").addClass("uk-form-row uk-accordion-content").append(report)
        ).append(
            $("<h3/>").addClass("uk-accordion-title").text("List of publications (Optional)"),
            $("<div/>").addClass("uk-form-row uk-accordion-content").append(doi)
        ).append(
            $("<h3/>").addClass("uk-accordion-title").text("Training activity (Optional)"),
            $("<div/>").addClass("uk-form-row uk-accordion-content").append(training)
        ).append(
            $("<h3/>").addClass("uk-accordion-title").text("Hiring (Optional)"),
            $("<div/>").addClass("uk-form-row uk-accordion-content").append(hiring)
        ).append(
            $("<div/>").addClass("uk-form-row").append(upload)
        ).append(
            $("<input/>").attr({"type": "hidden", "name": "image_1"})
        ).append(
            $("<input/>").attr({"type": "hidden", "name": "image_2"})
        ).append(
            $("<input/>").attr({"type": "hidden", "name": "image_3"})
        );
        var pop = dialog(form.prop("outerHTML"), function() {
            var data = {
                "doi": $("textarea[name=doi]").val(),
                "report": $("textarea[name=report]").val(),
                "training": $("textarea[name=training]").val(),
                "hiring": $("textarea[name=hiring]").val(),
                "image_1": $("input[name=image_1]").val(),
                "image_2": $("input[name=image_2]").val(),
                "image_3": $("input[name=image_3]").val()
            };
            let url = "{0}/{1}".f(window.proj.url.activity, name);
            json_send(url, data).done(function (reply) {
                if (reply.message) {
                    UIkit.notify(reply.message, {
                        timeout: 3000,
                        status: "success"
                    });
                }
                pop.hide();
            });
        }, function () {
            window.render.clean_activity(name);
        });
        if(pop.isActive()){
            $("div#upload").dropzone({
                url: window.proj.url.activity_upload,
                params: {"project": name},
                withCredentials: true,
                maxFilesize: 3, // 3 Mb maximum file size
                maxFiles: 3,
                //autoProcessQueue: false,
                addRemoveLinks: true,
                acceptedFiles: 'image/*'
                ,maxfilesexceeded: function(file) {
                    this.removeFile(file);
                }
                ,success: function(image, response){
                    image.server_name = window.render.hidden_field(response);
                }
                ,canceled: function(file){
                    this.removeFile(file);
                }
                ,removedfile: function(file){
                    if(file.server_name){
                        window.render.delete_activity(name, file.server_name);
                    }
                    $(file.previewElement).remove();
                }
                //forceFallback: true
            });
        }
    };

    $(document).on("ready", function(){
        var active = $.trim( $("#active_project").data("ids") ).split(",");
        $.each(active, function(key, value){
            window.render.modal("{0}/{1}".f(window.proj.url.modal_allocate, value), "renew");
            window.render.modal("{0}/{1}".f(window.proj.url.modal_transform, value), "transform");
            window.render.modal("{0}/{1}".f(window.proj.url.modal_assign, value), "assign", window.render.user_list);
        });
        var inactive = $.trim( $("#inactive_project").data("ids") ).split(",");
        $.each(inactive, function(key, value){
            window.render.modal("{0}/{1}".f(window.proj.url.modal_activate, value), "activate");
        });
    });

    $(document).on("click", ".responsible_ass", window.render.assign_responsible);
    $(document).on("click", ".activity", window.render.activity);
    $(document).on("click", ".history", window.render.project_history);

    $(document).on("click", ".assign", window.render.window_visibility_control);
    $(document).on("click", ".renew", window.render.window_visibility_control);
    $(document).on("click", ".extend", window.render.window_visibility_control);
    $(document).on("click", ".activate", window.render.window_visibility_control);
    $(document).on("click", ".transform", window.render.window_visibility_control);

    $(document).on("click", ".assign_submit", window.render.new_user);
    $(document).on("click", ".activate_submit", window.render.activate);
    $(document).on("click", ".extension_submit", window.render.extend);
    $(document).on("click", ".transform_submit", window.render.transform);
    $(document).on("click", ".window_hide", window.render.window_visibility_control);
    $(document).on("click", ".remove", window.render.remove_user); //the buttons could be created on the fly

    $(document).on("blur", "input,textarea", window.render.input_empty);
    $(document).on("focus blur keyup open close", ".assign_form", window.render.shadow);
})(window, document, jQuery);