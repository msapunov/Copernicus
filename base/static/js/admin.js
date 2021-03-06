(function(window, document, $, undefined){
    "use strict";
    window.admin = {};
    window.admin.url = {
        accept: "admin/registration/accept",  // Temporary handler to be removed
        approve: "admin/registration/approve",
        create: "admin/registration/create",
        reject: "admin/registration/reject",
        ignore: "admin/registration/ignore",
        info: "admin/partition/info",
        history: "admin/history",
        message: "admin/message/register",
        new_users: "admin/registration/users",
        sinfo: "admin/slurm/nodes/list",
        system: "admin/sys/info",
        tasks: "admin/tasks/list",
        tasks_accept: "admin/tasks/accept",
        tasks_history: "admin/tasks/history",
        tasks_ignore: "admin/tasks/ignore",
        tasks_reject: "admin/tasks/reject",
        tasks_update: "admin/tasks/update",
        user: "admin/user/info",
        user_details: "admin/user/details/get",
        user_create: "admin/user/create",
        user_edit: "admin/user/details/set",
        user_delete: "admin/user/delete",
        user_purge: "admin/user/purge",
        user_p_reset: "admin/user/password",
        visa: "admin/registration/visa",
    };
    window.admin.sys = function(){
        json_send(window.admin.url.system).done(function(data){
            if(!data){
                alert("No data placeholder")
            }
            var donne = data.data;
            var system_body = $("#system_body");
            var tmp_div = $("<div/>");
            $.each(donne, function(idx, value){
                var sys_info = window.render.sys(value);
                sys_info.appendTo(tmp_div);
            });
            system_body.html(tmp_div);
        });
    };
    window.render = {};
    window.sort_by = function(field, reverse, primer){
        var key = primer ?
        function(x) {return primer(x[field])} :
        function(x) {return x[field]};

        reverse = !reverse ? 1 : -1;
        return function (a, b) {
            return a = key(a), b = key(b), reverse * ((a > b) - (b > a));
        }
    };
    window.render.tasks_sel_update = function(){
        var data = $(this).data("id");
        var selectors = $("#"+data).find("select");
        $.each(selectors, function(idx, el){
            var val = $(el).attr("data-val");
            if(val != "") {
                $(el).val(val);
            }
        });
    };
    window.render.tasks_btn_toggle = function(){
        var tid = $(this).data("tid");
        $(".task_btn_" + tid).prop("disabled", false);
    };
    window.render.tasks_edit = function(){
        $(this).prop("disabled", true);
        var tid = $(this).attr("data-tid");
        var selectors = $("#history-" + tid + ".ext_info").find("select");
        var data = {};
        $.each(selectors, function(idx, el){
            data[ $(el).attr("name") ] = $(el).val();
        });
        var url = window.admin.url.tasks_update + "/" + tid;

        json_send(url, data, true).done(function(data){
            var stat = $(".task_status_" + tid);
            var st_value = data.data.status;
            if ((st_value === undefined) || (st_value === null)){
                st_value = "";
            }
            stat.text(st_value.toString());

            var deci = $(".task_decision_" + tid);
            var icon = window.render.decision_icon(data.data.decision);
            deci.html(icon.prop("outerHTML"));
        });
    };
    window.render.render_manage = function(val){
        var tid = val.id;
        var td_hdn = $("<td/>").attr({"colspan": 4}).addClass("uk-form");
        var ul = $("<ul/>");
        var keys = ["description", "author", "created", "modified", "approve"];
        var opts = ["pending", "processed", "done", "decision"];
        var all = $.merge($.merge([], keys), opts);
        $.each(all, function(idx, prop){
            var value = val[prop];
            if((value === undefined)||(value === null)){
                value = "";
            }else {
                value = value.toString();
            }
            if($.inArray(prop, keys) >= 0) {
                $("<li/>").text(prop.capitalize() + ": " + value).appendTo(ul);
            }else{
                var txt = prop.capitalize();
                var sel = $("<select/>").addClass("task_sel_info").width("100%");
                sel.append(new Option(txt + ": Undefined", ""));
                if (prop == "decision"){
                    sel.append(new Option(txt + ": Accept", "accept"));
                    sel.append(new Option(txt + ": Reject", "reject"));
                    sel.append(new Option(txt + ": Ignore", "ignore"));
                }else{
                    sel.append(new Option(txt + ": True", "true"));
                    sel.append(new Option(txt + ": False", "false"));
                }
                sel.attr({"data-val": value, "data-tid": tid, "name": prop});
                $("<li/>").append(sel).appendTo(ul);
            }
        });
        td_hdn.append(ul);

        var btn = $("<button/>").text("Apply").addClass("uk-button task_edit");
        btn.attr({"type": "button", "data-tid": tid}).prop("disabled",true);
        btn.addClass("task_btn_" + tid);

        td_hdn.append(btn);
        return td_hdn;
    };
    window.render.render_task_item = function(val){
        var td_hdn = $("<td/>").attr({"colspan": 4});
        var ul = $("<ul/>");
        var keys = ["description", "author", "created", "pending"];
        keys = $.merge(keys, ["processed", "done", "modified", "approve", "decision"]);
        $.each(keys, function(idx, prop){
            $("<li/>").text(prop.capitalize() + ": " + val[prop]).appendTo(ul);
        });
        td_hdn.append(ul);
        return td_hdn;
    };
    window.render.decision_icon = function(decision){
        var icon = $("<span/>");
        if(decision === "accept"){
            icon.addClass("uk-icon-thumbs-o-up");
        }else if(decision === "ignore"){
            icon.addClass("uk-icon-thumbs-o-down");
        }else if(decision === "reject"){
            icon.addClass("uk-icon-thumbs-down");
        }
        return icon
    };
    window.render.render_task = function(val, item){
        var icon = window.render.decision_icon(val.decision);

        var btn_span = $("<span/>").addClass("uk-icon-plus");
        var btn = $("<button/>").attr({"data-id": "history-"+val.id});
        btn.addClass("uk-button uk-button-mini history_info");
        btn.append(btn_span);
        var td_btn = $("<td/>").append(btn);
        var td_act = $("<td/>").addClass("uk-text-nowrap").text(val.action);
        var td_stat = $("<td/>").addClass("task_status_" + val.id).text(val.status);
        var td_decision = $("<td/>").addClass("uk-text-center task_decision_" + val.id);
        td_decision.prop("title", val.decision).append(icon);

        var tr = $("<tr/>");
        tr.append(td_btn).append(td_act).append(td_stat);
        tr.append(td_decision);

        if(item) {
            var td_hdn = window.render.render_task_item(val);
        }else{
            var td_hdn = window.render.render_manage(val);
        }

        var tr_hdn = $("<tr/>").attr({"id": "history-"+val.id});
        tr_hdn.addClass("ext_info uk-hidden");
        tr_hdn.append(td_hdn);
        return tr.add(tr_hdn);
    };
    window.render.tasks_manage = function(){
        json_send(window.admin.url.tasks_history).done(function(data){
            if(data.data.length < 1){
                UIkit.notify("No tasks found!", {timeout: 2000, status:"primary"});
            }else{

                var table = $("<table/>").addClass("uk-table uk-table-hover uk-table-condensed");

                var thead = $("<thead/>");
                thead.append( $("<th/>") );
                thead.append( $("<th/>").text("Action") );
                thead.append( $("<th/>").text("Status") );
                thead.append( $("<th/>").text("Decision") );
                thead.appendTo(table);

                $.each(data.data, function(idx, val){
                    table.append(window.render.render_task(val, false));
                });

                $("#modal_body").html(table.prop("outerHTML"));
                var modal = UIkit.modal("#modal");
                if ( modal.isActive() ) {
                    modal.hide();
                } else {
                    modal.show();
                }
            }
        });
    };
    window.render.tasks_history = function(){
        json_send(window.admin.url.tasks_history).done(function(data){
            if(data.data.length < 1){
                UIkit.notify("No historic tasks found!", {timeout: 2000, status:"primary"});
            }else{

                var table = $("<table/>").addClass("uk-table uk-table-hover uk-table-condensed");

                var thead = $("<thead/>").append($("<th/>"));
                var head_act = $("<th/>").text("Action");
                var head_status = $("<th/>").text("Status");
                var head_decision = $("<th/>").text("Decision");

                thead.append(head_act);
                thead.append(head_status);
                thead.append(head_decision);

                thead.appendTo(table);

                $.each(data.data, function(idx, val){
                    table.append(window.render.render_task(val, true));
                });

                $("#modal_body").html(table.prop("outerHTML"));
                var modal = UIkit.modal("#modal");
                if ( modal.isActive() ) {
                    modal.hide();
                } else {
                    modal.show();
                }
            }
        });
    };
    window.render.task_row = function(val){
        var day = moment(val.created, "YYYY-MM-DD HH:mm Z");

        var b = $("<button/>").attr({"data-id": "task-"+val.id+"-child"});
        b.addClass("uk-button uk-button-mini task_info");
        b.append($("<span/>").addClass("uk-icon-plus"));
        var btn = $("<td/>").addClass("uk-width-1-10").append(b);

        var act = $("<td/>").addClass("uk-width-3-10 uk-text-nowrap");
        act.text(val.action);
        var data = $("<td/>").addClass("uk-width-3-10 uk-text-truncate");
        data.text(day.format("L"));

        var tr = $("<tr/>").attr({"id": "task-"+val.id+"-parent"});

        tr.append(btn).append(act).append(data);
        return tr

    };
    window.render.task_hidden_row = function(val){

        var btn_grp = $("<div/>").addClass(
            "uk-button-group uk-float-right uk-margin-top"
        );

        var s_accept = $("<span/>").addClass("uk-icon-thumbs-o-up uk-margin-small-right");
        var btn_accept = $("<button/>").attr({"data-id": val.id});
        btn_accept.addClass("uk-button task_accept").append(s_accept).append("Accept");

        var s_ignore = $("<span/>").addClass("uk-icon-thumbs-o-down uk-margin-small-right");
        var btn_ignore = $("<button/>").attr({"data-id": val.id});
        btn_ignore.addClass("uk-button task_ignore").append(s_ignore).append("Ignore");

        var s_reject = $("<span/>").addClass("uk-icon-thumbs-down uk-margin-small-right");
        var btn_reject = $("<button/>").attr({"data-id": val.id}).append(s_reject).append("Reject");
        btn_reject.addClass("uk-button task_reject uk-button-danger");

        $.each([btn_accept, btn_ignore, btn_reject], function(idx, el){
            el.appendTo(btn_grp);
        });

        var ul = $("<ul/>");
        $.each(["description", "author", "created"], function(idx, prop){
            $("<li/>").text(prop.capitalize() + ": " + val[prop]).appendTo(ul);
        });

        var td_hdn = $("<td/>").attr({"colspan": 5});
        td_hdn.append(ul);
        td_hdn.append(btn_grp);

        var tr_hdn = $("<tr/>").attr({"id": "task-"+val.id+"-child"});
        tr_hdn.addClass("ext_info uk-hidden");
        return tr_hdn.append(td_hdn)
    };
    window.render.tasks = function(){
        json_send(window.admin.url.tasks).done(function(data){
            if(data.data.length < 1){
                UIkit.notify("No new pending tasks found!",{timeout: 2000, status:"primary"});
            }else{

                var table = $("<table/>").addClass(
                    "uk-table uk-table-hover uk-table-condensed"
                );

                var head_empty = $("<th/>");
                var head_act = $("<th/>").text("Action");
                var head_created = $("<th/>").text("Created");

                var th = $("<thead/>").append(head_empty).append(head_act).append(head_created);
                table.append(th);

                $.each(data.data, function(idx, val){

                    var row = window.render.task_row(val);
                    var hidden = window.render.task_hidden_row(val);

                    table.append(row);
                    table.append(hidden);

                });

                $("#modal_body").html(table.prop("outerHTML"));

                var modal = UIkit.modal("#modal");
                if ( modal.isActive() ) {
                    modal.hide();
                } else {
                    modal.show();
                }
                modal.on({'hide.uk.modal': function(){
                    window.render.tasks_reload();
                    modal.off('hide.uk.modal');
                }});

            }
        });
    };
    window.render.sys = function(data){
        var div = $("<div/>");
        $("<h3/>").append(data.server).appendTo(div);
        var ul = $("<ul/>").appendTo(div);
        var user = $("<span/>").attr({"class": "user_show"}).append(data.uptime.users);
        $("<li/>").append("Users: ").append($("<a/>").attr({"class": "user_show"}).text(data.uptime.users).data("data", data.server)).appendTo(ul);

        var load_1 = data.uptime.load_1;
        var load_5 = data.uptime.load_5;
        var load_15 = data.uptime.load_15;
        $("<li/>").append("Load: "+load_1+", "+load_5+", "+load_15).appendTo(ul);
        ul.appendTo(div);
        $("<p/>").append("Memory usage: "+data.mem.mem_usage).appendTo(div);
        var progress = $("<div/>").attr({"class": "uk-progress uk-progress-mini uk-progress-striped"});
        $("<div/>").attr({"class": "uk-progress-bar"}).css("width", data.mem.mem_usage).appendTo(progress);
        progress.appendTo(div);
        $("<p/>").append("Swap usage: "+data.mem.swap_usage).appendTo(div);
        var swap_prog = $("<div/>").attr({"class": "uk-progress uk-progress-mini uk-progress-striped"});
        $("<div/>").attr({"class": "uk-progress-bar"}).css("width", data.mem.swap_usage).appendTo(swap_prog);
        swap_prog.appendTo(div);
        return div;
    };
    window.render.user=function(){
        var data = $(this).data("data");
        json_send(window.admin.url.user, {server: data}).done(function(data){
            var table = $("<table>").addClass("uk-table uk-table-hover uk-table-striped uk-table-condensed");
            data.data.sort(window.sort_by("username", false, function(a){return a.toUpperCase()}));
            $.each(data.data, function(idx, val){
                var user = $("<td/>").text(val.username);
                var from = $("<td/>").text(val.from);
                var proc_data = val.process.replace(/ /g, "&nbsp;");
                var proc = $("<td/>").html(proc_data);
                $("<tr/>").append(user).append(from).append(proc).appendTo(table);
            });
            $("#modal_body").html(table.prop("outerHTML"));

            var modal = UIkit.modal("#modal");
            if ( modal.isActive() ) {
                modal.hide();
            } else {
                modal.show();
            }
        });
    };
    window.render.partition=function(){
        json_send(window.admin.url.info).done(function(data){
            var tbody = $("<tbody/>").attr({"id": "slurm"});
            data.data.sort(window.sort_by("total", true, parseInt));
            $.each(data.data, function(idx, val){
                var name = $("<td/>").text(val.name);
                var allo = $("<td/>").text(val.allocated);
                var idle = $("<td/>").text(val.idle);
                var other = $("<td/>").text(val.other);
                var total = $("<td/>").text(val.total);
                $("<tr/>").append(name).append(allo).append(idle).append(other).append(total).appendTo(tbody);
            });
            $("#slurm").replaceWith(tbody);
        });
    };
    window.render.new_project=function(){
        var data = $(this).data("id");
        $("#"+data).toggleClass("uk-hidden");
        $(this).closest("tr").eq(0).toggleClass("ext_info");
        $(this).find("span").eq(0).toggleClass("uk-icon-plus uk-icon-minus");
    };
    window.render.message=function(){
        var id = $(this).data("id");
        var mail = $(this).data("addr");
        var title = "Send message to {0}?".f(mail);
        var placeholder = "Type your message";
        var motiv = $("<textarea/>").addClass("uk-width-1-1").attr({
            "rows": "4",
            "name": "note",
            "placeholder": placeholder
        });
        var form = $("<form/>").addClass("uk-form").append(
            $("<legend/>").text(title)
        ).append(
            $("<div/>").addClass("uk-form-row").append(motiv)
        );
        var popup = dialog(form.prop("outerHTML"), function(){
            var data = {
                "note": $("textarea[name=note]").val(),
                "project": id
            };
            json_send(window.admin.url.message, data).done(function(reply){
                if(reply.data){
                    UIkit.notify(reply.data, {timeout: 2000, status:"success"});
                }
                popup.hide();
            });
        });
    };
    window.render.new_ignore=function(){
        var id = $.trim( $(this).data("id") );
        var mid = $.trim( $(this).data("meso") );
        var msg = "Ignore project {0}? Are you sure?".f(mid);
        UIkit.modal.confirm(msg, function(){
            var url = window.admin.url.ignore + "/" + id;
            json_send(url, {
                "pid": id
            }).done(function(reply){
                if(reply.data){
                    UIkit.notify(reply.data, {timeout: 2000, status:"success"});
                }
                $("#"+id).remove();
                $("#"+id+"-info").remove();
            });
        });
    };
    window.render.new_create=function(){
        var id = $.trim( $(this).data("id") );
        var mid = $.trim( $(this).data("meso") );
        var project_title = $.trim( $(this).data("title") );
        var title = "Project: {0}".f(project_title);
        var name = "Registration ID: {0}".f(mid);
        var text = "Create project record and correspondent task in the task queue?";
        var checkbox = $("<input>").attr({
            "id": "safety_checkbox",
            "name": "safety",
            "type": "checkbox"
        }).addClass("uk-margin-small-right uk-form-danger");
        var label = $("<label/>").attr('for', "safety_checkbox");
        label.text("I do confirm that all bureaucratic procedures are finished");
        var express = $("<div/>").addClass(
            "uk-form-row uk-alert uk-alert-danger"
        );
        express.append(checkbox).append(label);

        var conf = [title, name, text, express.prop("outerHTML")].join("<br>");
        var url = window.admin.url.create + "/" + id;
        UIkit.modal.confirm(conf, function(){
            var safety = $("input[name=safety]").is(':checked') ? true : false;
            json_send(url, {"safety": safety}).done(function(reply){
                if(reply.data){
                    UIkit.notify(reply.data, {timeout: 2000, status:"success"});
                }
                $("#"+id).remove();
                $("#"+id+"-info").remove();
            });
        });
    };
    window.render.new_reject=function(){
        var id = $.trim( $(this).data("id") );
        var mid = $.trim( $(this).data("meso") );
        var project_title = $.trim( $(this).data("title") );
        var title = "Reject project {0}?".f(mid);
        var text = "Enter a reason for rejecting project '{0}' ({1})".f(project_title, mid);
        var motiv = $("<textarea/>").html(text).addClass("uk-width-1-1").attr({
            "rows": "4",
            "name": "note"
        });
        var form = $("<form/>").addClass("uk-form").append(
            $("<legend/>").text(title)
        ).append(
            $("<div/>").addClass("uk-form-row").append(motiv)
        );
        UIkit.modal.confirm(form.prop("outerHTML"), function(){
            var comment = $("textarea[name=note]").val();
            var url = window.admin.url.reject + "/" + id;
            json_send(url, {"note": comment}).done(function(reply){
                if(reply.data){
                    UIkit.notify(reply.data, {timeout: 2000, status:"success"});
                }
                $("#"+id).remove();
                $("#"+id+"-info").remove();
            });
        });
    };
    window.render.new_accept=function(){
        var id = $.trim( $(this).data("id") );

        var mid = $.trim( $(this).data("meso") );
        var project_title = $.trim( $(this).data("title") );
        var title = "Accepting project {0}".f(mid);
        var text = "Enter a reason for accepting project '{0}' ({1})".f(project_title, mid);
        var motiv = $("<textarea/>").html(text).addClass("uk-width-1-1").attr({
            "rows": "4",
            "name": "note"
        });
        var form = $("<form/>").addClass("uk-form").append(
            $("<legend/>").text(title)
        ).append(
            $("<div/>").addClass("uk-form-row").append(motiv)
        );
        UIkit.modal.confirm(form.prop("outerHTML"), function(){
            var comment = $("textarea[name=note]").val();
            var url = window.admin.url.accept + "/" + id;
            json_send(url, {"note": comment}).done(function(reply){
                if(reply.data){
                    UIkit.notify(reply.data, {timeout: 2000, status:"success"});
                }
                $("#"+id).remove();
                $("#"+id+"-info").remove();
            });
        });
    };
    window.render.new_visa=function(){
        var id = $.trim( $(this).data("id") );
        var mid = $.trim( $(this).data("meso") );
        var project_title = $.trim( $(this).data("title") );
        var title = "Project: {0}".f(project_title);
        var name = "Registration ID: {0}".f(mid);
        var text = "Create and send visa to responsible person?";
        var checkbox = $("<input>").attr({
            "id": "visa_checkbox",
            "name": "visa_exception",
            "type": "checkbox"
        }).addClass("uk-margin-small-right uk-form-danger");
        var label = $("<label/>").attr('for', "visa_checkbox");
        label.text("Select checkbox if project does not require a signed visa");
        var express = $("<div/>").addClass(
            "uk-form-row uk-alert uk-alert-danger"
        );
        express.append(checkbox).append(label);

        var conf = [title, name, text, express.prop("outerHTML")].join("<br>");
        var url = window.admin.url.visa + "/" + id;
        UIkit.modal.confirm(conf, function(){
            var exception = $("input[name=visa_exception]").is(':checked') ? true : false;
            json_send(url, {"visa": exception}).done(function(reply){
                if(reply.data){
                    UIkit.notify(reply.data, {timeout: 2000, status:"success"});
                }
                var app_id = "#approval_msg_{0}".f(id);
                $(app_id).append(
                    $("<div/>").addClass("uk-badge uk-badge-success").html("Visa done")
                );
                var ico_id = "#approval_ico_{0}".f(id);
                $(ico_id).addClass("uk-icon-edit").addClass("uk-text-warning");
                $(ico_id).removeClass("uk-icon-wrench").removeClass("uk-text-success");
                window.render.visaBtnReplace(btn);
            });
        });
    };
    window.render.new_approve=function(){
        var btn = $(this);
        var id = $.trim( $(this).data("id") );
        var mid = $.trim( $(this).data("meso") );
        var project_title = $.trim( $(this).data("title") );
        var title = "Project: {0}".f(project_title);
        var name = "Registration ID: {0}".f(mid);
        var text = "Do you confirm that software requirements indicated in numerical methods field can be satisfied?";
        var conf = [title, name, text].join("<br>");
        var url = window.admin.url.approve + "/" + id;
        UIkit.modal.confirm(conf, function(){
            json_send(url).done(function(reply){
                if(reply.data){
                    UIkit.notify(reply.data, {timeout: 2000, status:"success"});
                }
                var app_id = "#approval_msg_{0}".f(id);
                $(app_id).append(
                    $("<div/>").addClass("uk-badge uk-badge-success").html(
                        "Technical approval granted")
                );
                var ico_id = "#approval_ico_{0}".f(id);
                $(ico_id).addClass("uk-icon-wrench").addClass("uk-text-success");
                $(ico_id).removeClass("uk-icon-question").removeClass("uk-text-primary");
                window.render.approveBtnReplace(btn);
            });
        });
    };
    window.render.tasks_reload=function(){
        json_send(window.admin.url.tasks).done(function(data){
            var tasks = 0;
            if(data.data.length < 1){
                UIkit.notify("No pending tasks found!", {timeout: 2000, status:"primary"});
            }else{
                tasks = data.data.length;
            }
            $("#taks_queue_length").text(tasks);
        });
    };
    window.render.tasks_act=function(action, btn){
        var id = $(btn).data("id");
        var url = window.admin.url.tasks_ignore;
        if(action==="accept"){
            url = window.admin.url.tasks_accept;
        }else if(action==="reject"){
            url = window.admin.url.tasks_reject;
        }
        url += "/" + id;
        json_send(url, {task: id}, true).done(function(data){
            $("#taks_queue_length").text(data.data.length);
            var tr = $(btn).closest("tr").eq(0);
            var el_id = tr.attr('id');
            var del_id = el_id.replace("child", "parent");
            tr.remove();
            $("#"+del_id).remove();
            if(data.data.length < 1){
                UIkit.modal("#modal").hide();
            }
        });
    };
    window.render.visaBtnReplace=function(btn){
        btn.removeClass("new_visa").addClass("new_resend_visa");
        var span = btn.find("span")[0];
        btn.html(span.outerHTML + "Re-send Visa");
    };
    window.render.approveBtnReplace=function(btn){
        btn.removeClass("new_approve").addClass("new_visa");
        var span = btn.find("span")[0];
        $(span).removeClass("uk-icon-wrench").addClass("uk-icon-edit");
        btn.html(span.outerHTML + "Send Visa");
    };
    window.render.name_swap=function(){
        var name_el, surname_el, name, surname;
        name_el = $("#ua_name");
        surname_el = $("#ua_surname");
        name = name_el.val();
        surname = surname_el.val();
        name_el.val(surname);
        surname_el.val(name);
    };
    window.render.form_reset=function(){
        var ids;
        ids = ["#ua_id","#ua_login","#ua_name","#ua_surname","#ua_email"];
        $.each(ids, function(idx, name){
            $(name).val("");
        });
        ids = ["#ua_active","#ua_user","#ua_resp","#ua_comm","#ua_admn"];
        $.each(ids, function(idx, name){
            $(name).prop("checked", false);
        });
        $("#ua_current").text("None");
        $("#ua_project").val('').trigger('chosen');
    };
    window.render.user_add=function() {
        window.render.form_reset();
        if ($(this).hasClass("user_edit")) {
            window.render.user_edit(this);
        }
        var modal = UIkit.modal("#user_change");
        if ( modal.isActive() ) {
            modal.hide();
        } else {
            modal.show();
        }
    };
    window.render.user_edit=function(btn){
        var id = $.trim( $(btn).data("id") );
        var url = window.admin.url.user_details + "/" + id;
        json_send(url, false, false).done(function(reply) {
            if(! reply.data){
                UIkit.notify("No data returned by service", {timeout: 2000, status:"danger"});
                return
            }
            var data = reply.data;
            $("#ua_id").val(data.id ? data.id : '');
            $("#ua_login").val(data.login ? data.login : '');
            $("#ua_name").val(data.name ? data.name : '');
            $("#ua_surname").val(data.surname ? data.surname : '');
            $("#ua_email").val(data.email ? data.email : '');
            $("#ua_active").prop('checked', data.active);
            $("#ua_user").prop('checked', data.user);
            $("#ua_resp").prop('checked', data.responsible);
            $("#ua_comm").prop('checked', data.committee);
            $("#ua_admn").prop('checked', data.admin);
            $("#ua_current").text(data.projects.join(", "));
            $("#ua_project").val(data.projects).multiselect("refresh");
        });
    };
    window.render.ue_buttons=function(id, login){
        var s_reset = $("<span/>").addClass("uk-icon-eraser");
        var btn_reset = $("<button/>").attr({"data-id": id, "type": "button"}).append(s_reset);
        btn_reset.addClass("uk-button uk-button-mini user_password_reset");

        var s_edit = $("<span/>").addClass("uk-icon-cogs");
        var btn_edit = $("<button/>").attr({"data-id": id, "type": "button"}).append(s_edit);
        btn_edit.addClass("uk-button uk-button-mini user_edit");

        var s_del = $("<span/>").addClass("uk-icon-close");
        var btn_del = $("<button/>").attr({"data-id": id, "data-login": login, "type": "button"}).append(s_del);
        btn_del.addClass("uk-button uk-button-mini user_purge uk-button-danger");

        var btn_grp = $("<div/>").addClass(
            "uk-button-group uk-float-right"
        );

        $.each([btn_reset, btn_edit, btn_del], function(idx, el){
            el.appendTo(btn_grp);
        });

        return $("<td/>").append(btn_grp)
    };
    window.render.update_ue=function(reply){
        if(!reply.data) {
            return false;
        }
        var data = reply.data;
        var id = data.id;

        var login = $("<td/>").text(data.login);
        var name = $("<td/>").addClass("uk-text-capitalize").text(data.name);
        var surname = $("<td/>").addClass("uk-text-capitalize").text(data.surname);
        var status = $("<td/>");
        if(data.active){
            status.append( $("<span/>").addClass("uk-icon-check") )
        }

        var buttons = window.render.ue_buttons(id, data.login);

        var tr = $("<tr/>").attr({"id": "ue_rec_"+id}).append(login).append(name);
        tr.append(surname).append(status).append(buttons);
        $("tr#ue_rec_"+id).replaceWith(tr);
    };
    window.render.tasks_accept=function(){
        window.render.tasks_act("accept", this);
    };
    window.render.tasks_ignore=function(){
        window.render.tasks_act("ignore", this);
    };
    window.render.tasks_reject=function(){
        window.render.tasks_act("reject", this);
    };
    window.render.update_project_list=function(){
        var data=[];
        $(this).find('option:selected').each(function() {
            data.push( $(this).text() );
        });
        if(data.length > 0){
            $("#ua_current").text(data.join(", "));
        }else{
            $("#ua_current").text("None");
        }
    };
    window.render.ue_submit_or_cancel=function(){
        if($(this).hasClass("ue_submit")){

            var data = {};
            var ids = ["#csrf_token", "#ua_id","#ua_login","#ua_name","#ua_surname","#ua_email","#ua_project"];
            $.each(ids, function(idx, id){
                var name = $(id).prop("name");
                data[name] = $(id).val();
            });
            var ids = ["#ua_active","#ua_user","#ua_resp","#ua_comm","#ua_admn"];
            $.each(ids, function(idx, id){
                var name = $(id).prop("name");
                data[name] = $(id).prop("checked") ? "y" : "";
            });

            //var data = $("form#ue_form").serializeArray().map(function(x){this[x.name] = x.value; return this;}.bind({}))[0];
            var uid = data.uid;
            if(uid === "" ){
                var url = window.admin.url.user_create;
            }else{
                var url = window.admin.url.user_edit;
            }
            json_send(url, data, false).done(function(reply){
                if(reply.message){
                    UIkit.notify(reply.message, {timeout: 2000, status:"success"});
                }
                window.render.update_ue(reply);
            })
        }
        UIkit.modal("#user_change").hide();
    };
    window.render.user_password_reset=function(msg, url){
        UIkit.modal.confirm(msg, function(){
            json_send(url,false).done(function(reply){
                if(reply.data && reply.data === ""){
                    if(reply.message){
                        UIkit.notify(reply.message, {timeout: 2000, status:"success"});
                    }
                }
            });
        });
    };
    window.render.destroy=function(url, id){
        var url = url + "/" + id;
        json_send(url,false).done(function(reply){
            if(reply.message){
                UIkit.notify(reply.message, {timeout: 2000, status:"success"});
            }
            if(reply.data && reply.data === true){
                $("tr#ue_rec_"+id).remove();
            }
        });
    };
    window.render.user_purge=function(){
        var id = $.trim( $(this).data("id") );
        var login = $.trim( $(this).data("login") );
        var msg1 = "<p>Delete user {0} from the data base? Are you sure?".f(login);
        var msg2 = "<p><input type='checkbox' id='purge_chk'> Delete user account and user files too?";
        var msg = msg1 + msg2;
        UIkit.modal.confirm(msg, function(){
            if($("#purge_chk").prop("checked") === true){
                var url = window.admin.url.user_purge;
            }else{
                var url = window.admin.url.user_delete;
            }
            window.render.destroy(url, id);
        });
    };
    window.render.pass_reset=function(){
        var id = $.trim( $(this).data("id") );
        var login = $.trim( $(this).data("login") );
        var mail = $.trim( $(this).data("mail") );
        var msg = "<p>Reset the login password for {0}?<p>An e-mail with the new password will be sent to {1}<p>Are you sure?".f(login, mail);
        var url = window.admin.url.user_p_reset + "/" + id;
        window.render.user_password_reset(msg, url);
    };

    $(document).on("ready", function(){
        $.fn.dataTable.ext.buttons.refresh = {
            text: "<span class='uk-icon-refresh uk-margin-small-right'></span>&nbsp;Reload",
            className: "uk-button uk-button-small uk-margin-small-top",
            init: function(api, node, config) {
                $(node).removeClass("dt-button")
            },
            action: function( e, dt, node, config ){
                dt.clear().draw();
                dt.ajax.reload();
            }
        };
        window.admin.sys();
        $("#events").DataTable();
        $("#sinfo").DataTable({
            "ajax": {"type": "POST", "url": window.admin.url.sinfo},
            dom: 'tiB',
            buttons: {
                className: 'copyButton',
                buttons: [ 'refresh' ]
            },
            "paging": false,
            "searching": false,
            "columns": [
                    {"data": "node"},
                    {"data": "reason"},
                    {"data": "date"},
                    {"data": "status"}
                ]
        });
    });
    $(document).on("click", ".user_show", window.render.user);
    $(document).on("click", ".system_reload", window.admin.sys);
    $(document).on("click", ".slurm_reload", window.render.partition);
    $(document).on("click", ".message", window.render.message);

    $(document).on("click", ".new_project", window.render.new_project);
    $(document).on("click", ".new_create", window.render.new_create);
    $(document).on("click", ".new_approve", window.render.new_approve);
    $(document).on("click", ".new_visa", window.render.new_visa);
    $(document).on("click", ".new_resend_visa", window.render.new_resend_visa);
    $(document).on("click", ".new_accept", window.render.new_accept);
    $(document).on("click", ".new_ignore", window.render.new_ignore);
    $(document).on("click", ".new_reject", window.render.new_reject);

    $(document).on("click", ".task_show", window.render.tasks);
    $(document).on("click", ".task_info", window.render.new_project);
    $(document).on("click", ".task_history", window.render.tasks_history);
    $(document).on("click", ".task_manage", window.render.tasks_manage);
    $(document).on("click", ".task_reload", window.render.tasks_reload);
    $(document).on("click", ".task_accept", window.render.tasks_accept);
    $(document).on("click", ".task_ignore", window.render.tasks_ignore);
    $(document).on("click", ".task_reject", window.render.tasks_reject);
    $(document).on("click", ".task_edit", window.render.tasks_edit);

    $(document).on("click", ".history_info", window.render.new_project);
    $(document).on("click", ".history_info", window.render.tasks_sel_update);

    $(document).on("click", ".user_add", window.render.user_add);
    $(document).on("click", ".user_edit", window.render.user_add);
    $(document).on("click", ".user_purge", window.render.user_purge);
    $(document).on("click", ".user_password_reset", window.render.pass_reset);
    $(document).on("click", ".name_swap", window.render.name_swap);
    $(document).on("click", ".ue_submit", window.render.ue_submit_or_cancel);
    $(document).on("click", ".ue_cancel", window.render.ue_submit_or_cancel);

    $(document).on("change", "#ua_project", window.render.update_project_list);
    $(document).on("change", ".task_sel_info", window.render.tasks_btn_toggle);

    $(document).on({
        mouseenter: function () {
            $("#task_btn_group").toggleClass("uk-hidden");
        },
        mouseleave: function () {
            $("#task_btn_group").toggleClass("uk-hidden");
        }
    }, "#tasks_info");


})(window, document, jQuery);