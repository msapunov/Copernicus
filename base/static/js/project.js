(function(window, document, $, undefined){
    "use strict";
    Dropzone.autoDiscover = false;
    window.proj = {};
    window.proj.url = {
        new_resp: "project/assign/responsible",
        user_list: "user/list",
        delete: "project/delete/user",
        history: "project/history",
        activity_upload: "project/activity/upload",
        activity_clean: "project/activity/clean",
        activity_delete: "project/activity/remove",
        modal_extend: "/project/modal/extend",
        modal_activity: "/project/modal/activity",
        modal_renew: "/project/modal/renew",
        modal_transform: "/project/modal/transform",
        modal_activate: "/project/modal/activate",
        modal_attach: "/project/modal/attach/user"
    };

    window.render = {};

    window.render.input_empty = function(){
        $(this).val().length < 1 ? $(this).addClass("uk-form-danger") : $(this).removeClass("uk-form-danger");
    };

    window.render.submit = function(url, e){
        var modal = $.trim( $(this).data("modal") );
        var form = $.trim( $(this).data("form") );
        var data = $("#" + form).serialize();
        ajax_send(url, data, modal);
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
                window.render.user_reshuffle(reply, p_object);
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
        return btn;
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
        json_send(window.proj.url.history, data).done(function(reply){
            if(reply.length > 0){
                window.render.history(reply, title);
            }else{
                UIkit.modal.alert("No history found for project {0}".f(name));
            }
        });
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
            var info;
            if(value.consumption){
                info = "{0}: {1}".f(value.fullname, value.consumption);
            }else{
                info = "{0}".f(value.fullname);
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
                break;
            }
        }
        return saved;
    };

    window.render.delete_activity = function(project, name){
        let url = "{0}/{1}/{2}".f(window.proj.url.activity_delete, project, name);
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

    window.render.dropzone = function(e){
        let name = $.trim( $(this).data("modal").split("_")[0] );
        trigger_modal.call(this);
        let dz = $("div#"+name+"_upload");
        if( $(dz)[0].dropzone ){
            return;
        };
        dz.dropzone({
            url: window.proj.url.activity_upload,
            params: {"project": name},
            withCredentials: true,
            maxFilesize: 3, // 3 Mb maximum file size
            maxFiles: 3,
            addRemoveLinks: true,
            acceptedFiles: 'image/*',
            maxfilesexceeded: function(file) {
                this.removeFile(file);
            },
            success: function(image, response){
                image.server_name = window.render.hidden_field(response);
            },
            canceled: function(file){
                this.removeFile(file);
            },
            removedfile: function(file){
                if(file.server_name){
                    window.render.delete_activity(name, file.server_name);
                }
                $(file.previewElement).remove();
            }
        });
    };

    window.render.dz_reset = function(e){
        var dz_parent = $(e.target).find(".dropzone");
        if(dz_parent.length > 0){
            $(dz_parent)[0].dropzone.removeAllFiles(true);
        }
    };

    $(document).on("ready", function(){
        // Loading modal windows for active projects
        var active = $.trim( $("#active_project").data("ids") ).split(",");
        $.each(active, function(key, value){
            modal("{0}/{1}".f(window.proj.url.modal_transform, value), "transform");
            modal("{0}/{1}".f(window.proj.url.modal_attach, value), "attach", window.render.user_list);
        });
        // Loading modal window for inactive projects ("Activate")
        var inactive = $.trim( $("#inactive_project").data("ids") ).split(",");
        $.each(inactive, function(key, value){
            modal("{0}/{1}".f(window.proj.url.modal_activate, value), "activate");
        });
        // Loading modal windows for the projects which could be renewed
        var renew = $.trim( $("#renew_project").data("ids") ).split(",");
        $.each(renew, function(key, value){
            modal("{0}/{1}".f(window.proj.url.modal_renew, value), "renew");
        });
        // Loading modal windows for the extendable projects
        var ext = $.trim( $("#extend_project").data("ids") ).split(",");
        $.each(ext, function(key, value){
            modal("{0}/{1}".f(window.proj.url.modal_extend, value), "extend");
            //modal("{0}/{1}".f(window.proj.url.modal_activity, value), "activity");
        });
    });

    $(document).on("click", ".responsible_ass", window.render.assign_responsible);
    $(document).on("click", ".history", window.render.project_history);

    $(document).on("click", ".attach", trigger_modal);
    $(document).on("click", ".renew", trigger_modal);
    $(document).on("click", ".extend", trigger_modal);
    $(document).on("click", ".activate", trigger_modal);
    $(document).on("click", ".transform", trigger_modal);
    $(document).on("click", ".activity", window.render.dropzone);

    $(document).on("click", ".attach_submit", window.render.submit);
    $(document).on("click", ".activate_submit", window.render.submit);
    $(document).on("click", ".extension_submit", window.render.submit);
    $(document).on("click", ".transform_submit", window.render.submit);
    $(document).on("click", ".activity_submit", window.render.submit);
    $(document).on("click", ".window_hide", trigger_modal);
    $(document).on("click", ".remove", window.render.remove_user); //the buttons could be created on the fly

    $(document).on("blur", "input,textarea", window.render.input_empty);
    $(document).on("focus blur keyup open close", ".attach_form", window.render.shadow);

    $(document).on("hide.uk.modal", window.render.dz_reset);

})(window, document, jQuery);