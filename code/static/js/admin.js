(function(window, document, $, undefined){
    "use strict";
    window.admin = {};
    window.admin.url = {
        accept: "admin/registration/accept",
        info: "admin/partition/info",
        history: "admin/history",
        message: "admin/message/register",
        new_users: "admin/registration/users",
        reject: "admin/registration/reject",
        system: "admin/sys/info",
        tasks: "admin/tasks/list",
        tasks_accept: "admin/tasks/accept",
        tasks_history: "admin/tasks/history",
        tasks_ignore: "admin/tasks/ignore",
        tasks_reject: "admin/tasks/reject",
        user: "admin/user/info"
    };

    window.admin.sys = function(){
        $.ajax({
            url: window.admin.url.system,
            type: "POST",
            cache: false
        }).done(function(data){
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
    }

    window.render.tasks_history = function(){
        $.ajax({
            url: window.admin.url.tasks_history,
            type: "POST",
            cache: false
        }).done(function(data){
            if(data.data.length < 1){
                UIkit.notify("No historic tasks found!", {timeout: 2000, status:"primary"});
            }else{

                var table = $("<table/>").addClass("uk-table uk-table-hover uk-table-condensed");

                var head_act = $("<th/>").text("Action");
                var head_author = $("<th/>").text("Author");
                var head_status = $("<th/>").text("Status");
                var head_approved = $("<th/>").text("Approved");
                var head_processed = $("<th/>").text("Processed");
                var head_decision = $("<th/>").text("Decision");
                var head_created = $("<th/>").text("Created");
                $("<thead/>").append($("<th/>")).append(head_act).append(head_author).append(head_status).append(head_approved).append(head_processed).append(head_decision).append(head_created).appendTo(table);

                //data.data.sort(window.sort_by("created", false, function(a){return a.toUpperCase()}));
                $.each(data.data, function(idx, val){
                    var btn = $("<td/>").append($("<button/>").attr({"data-id": "task-"+val.id}).addClass("uk-button uk-button-mini task_info").append($("<span/>").addClass("uk-icon-plus")));
                    var act = $("<td/>").addClass("uk-text-nowrap").text("{0} {1}".f(val.action, val.entity));
                    var task= $("<td/>").text(val.task);
                    var user = $("<td/>").text(val.author);
                    var status = $("<td/>").text(val.status);
                    var approved = $("<td/>").text(val.approved);
                    var processed = $("<td/>").text(val.processed);
                    var decision = $("<td/>").text(val.decision);
                    var data = $("<td/>").addClass("uk-text-nowrap").text(val.created);
                    $("<tr/>").append(btn).append(act).append(user).append(status).append(approved).append(processed).append(decision).append(data).appendTo(table);
                    $("<tr/>").attr({"id": "task-"+val.id}).addClass("ext_info uk-hidden").append( $("<td/>").text("Task: " + val.task).attr({"colspan": 7})).appendTo(table);
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
    }

    window.render.tasks = function(){
        $.ajax({
            url: window.admin.url.tasks,
            type: "POST",
            cache: false
        }).done(function(data){
            if(data.data.length < 1){
                UIkit.notify("No pending tasks found!", {timeout: 2000, status:"primary"});
            }else{

                var table = $("<table/>").addClass("uk-table uk-table-hover uk-table-condensed");

                var head_act = $("<th/>").text("Action");
                var head_author = $("<th/>").text("Author");
                var head_status = $("<th/>").text("Status");
                var head_created = $("<th/>").text("Created");
                $("<thead/>").append($("<th/>")).append(head_act).append(head_author).append(head_status).append(head_created).appendTo(table);

                //data.data.sort(window.sort_by("created", false, function(a){return a.toUpperCase()}));
                $.each(data.data, function(idx, val){
                // type="button" data-id='{{record.id}}-info'>
                    var btn = $("<td/>").append($("<button/>").attr({"data-id": "task-"+val.id+"-child"}).addClass("uk-button uk-button-mini task_info").append($("<span/>").addClass("uk-icon-plus")));
                    var act = $("<td/>").addClass("uk-text-nowrap").text("{0} {1}".f(val.action, val.entity));
                    var task= $("<td/>").text(val.task);
                    var user = $("<td/>").text(val.author);
                    var status = $("<td/>").text(val.status);
                    var data = $("<td/>").addClass("uk-text-nowrap").text(val.created);
                    $("<tr/>").attr({"id": "task-"+val.id+"-parent"}).append(btn).append(act).append(user).append(status).append(data).appendTo(table);
                    var btn_grp = $("<div/>").addClass("uk-button-group uk-float-right uk-margin-top");
                    var btn_accept = $("<button/>").attr({"data-id": val.id}).addClass("uk-button task_accept").append($("<span/>").addClass("uk-icon-thumbs-up uk-margin-small-right").text("Accept")).appendTo(btn_grp);
                    var btn_ignore = $("<button/>").attr({"data-id": val.id}).addClass("uk-button task_ignore").append($("<span/>").addClass("uk-icon-thumbs-o-down uk-margin-small-right").text("Ignore")).appendTo(btn_grp);
                    var btn_reject = $("<button/>").attr({"data-id": val.id}).addClass("uk-button task_reject uk-button-danger").append($("<span/>").addClass("uk-icon-thumbs-down uk-margin-small-right").text("Reject")).appendTo(btn_grp);

                    $("<tr/>").attr({"id": "task-"+val.id+"-child"}).addClass("ext_info uk-hidden").append( $("<td/>").text(val.human.capitalize()).attr({"colspan": 5}).append(btn_grp) ).appendTo(table);
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
    }
    window.render.sys = function(data){
        var div = $("<div/>");
        $("<h3/>").append(data.server).appendTo(div);
        var ul = $("<ul/>").appendTo(div);
        var user = $("<span/>").attr({"class": "user_show"}).append(data.uptime.users);
        $("<li/>").append("Users: ").append($("<a/>").attr({"class": "user_show"}).text(data.uptime.users).data("data", data.server)).appendTo(ul);

        var load_1 = data.uptime.load_1
        var load_5 = data.uptime.load_5
        var load_15 = data.uptime.load_15
        $("<li/>").append("Load: "+load_1+", "+load_5+", "+load_15).appendTo(ul);
        ul.appendTo(div);
        $("<p/>").append("Memory usage: "+data.mem.mem_usage).appendTo(div);
        var progress = $("<div/>").attr({"class": "uk-progress uk-progress-mini uk-progress-striped"});
        $("<div/>").attr({"class": "uk-progress-bar"}).css("width", data.mem.mem_usage).appendTo(progress);
        progress.appendTo(div)
        $("<p/>").append("Swap usage: "+data.mem.swap_usage).appendTo(div);
        var swap_prog = $("<div/>").attr({"class": "uk-progress uk-progress-mini uk-progress-striped"});
        $("<div/>").attr({"class": "uk-progress-bar"}).css("width", data.mem.swap_usage).appendTo(swap_prog);
        swap_prog.appendTo(div)
        return div;
    }

    window.render.user=function(){
        var data = $(this).data("data");
        $.ajax({
            url: window.admin.url.user,
            data: {server: data},
            type: "POST",
            cache: false
        }).done(function(data){
            var table = $("<table>").addClass("uk-table uk-table-hover uk-table-striped uk-table-condensed");
            data.data.sort(window.sort_by("username", false, function(a){return a.toUpperCase()}));
            $.each(data.data, function(idx, val){
                var user = $("<td/>").text(val.username);
                var from = $("<td/>").text(val.from);
                var proc_data = val.process.replace(/ /g, "&nbsp;")
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
    }

    window.render.partition=function(){
        $.ajax({
            url: window.admin.url.info,
            type: "POST",
            cache: false
        }).done(function(data){
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
    }

    window.render.new_project=function(){
        var data = $(this).data("id");
        $("#"+data).toggleClass("uk-hidden");
        $(this).closest("tr").eq(0).toggleClass("ext_info");
        $(this).find("span").eq(0).toggleClass("uk-icon-plus uk-icon-minus");
    }

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
    }

    window.render.new_reject=function(){
        var id = $.trim( $(this).data("id") );
        var mid = $.trim( $(this).data("meso") );
        var project_title = $.trim( $(this).data("title") );
        var title = "Rejecting project {0}".f(mid);
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
            json_send(window.admin.url.reject, {
                "pid": id,
                "note": comment
            }).done(function(reply){
                if(reply.data){
                    UIkit.notify(reply.data, {timeout: 2000, status:"success"});
                }
                $("#"+id).remove();
                $("#"+id+"-info").remove();
            });
        });
    }

    window.render.new_accept_users=function(id){
        $.ajax({
            url: window.admin.url.new_users,
            data: JSON.stringify({"pid": id}),
            type: "POST",
            cache: false
        }).done(function(data){
            var responsible = data.responsible;
            var users = data.users;
            var i = 0;
        });
    }

    window.render.new_accept=function(){
        var id = $.trim( $(this).data("id") );
        window.render.new_accept_users(id);

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
    }

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
        /*
        $.ajax({
            url: window.admin.url.tasks,
            type: "POST",
            cache: false
        }).done(function(data){
            var tasks = 0;
            if(data.data.length < 1){
                UIkit.notify("No pending tasks found!", {timeout: 2000, status:"primary"});
            }else{
                tasks = data.data.length;
            }
            $("#taks_queue_length").text(tasks);
        });
        */
    }
    window.render.tasks_act=function(action, btn){
        var id = $(btn).data("id");
        var url = window.admin.url.tasks_ignore;
        if(action=="accept"){
            url = window.admin.url.tasks_accept;
        }else if(action=="reject"){
            url = window.admin.url.tasks_reject;
        }
        json_send(url, {task: id}).done(function(data){
            var tr = $(btn).closest("tr").eq(0);
            var el_id = tr.attr('id');
            var del_id = el_id.replace("child", "parent")
            tr.remove();
            $("#"+del_id).remove();
        });
    }
    window.render.tasks_accept=function(){
        window.render.tasks_act("accept", this);
    }
    window.render.tasks_ignore=function(){
        window.render.tasks_act("ignore", this);
    }
    window.render.tasks_reject=function(){
        window.render.tasks_act("reject", this);
    }

    $(document).on("ready", function(){
        window.admin.sys();
    });
    $(document).on("click", ".user_show", window.render.user);
    $(document).on("click", ".system_reload", window.admin.sys);
    $(document).on("click", ".slurm_reload", window.render.partition);
    $(document).on("click", ".new_project", window.render.new_project);
    $(document).on("click", ".new_accept", window.render.new_accept);
    $(document).on("click", ".new_reject", window.render.new_reject);
    $(document).on("click", ".message", window.render.message);
    $(document).on("click", ".task_show", window.render.tasks);
    $(document).on("click", ".task_info", window.render.new_project);
    $(document).on("click", ".task_history", window.render.tasks_history);
    $(document).on("click", ".task_reload", window.render.tasks_reload);
    $(document).on("click", ".task_accept", window.render.tasks_accept);
    $(document).on("click", ".task_ignore", window.render.tasks_ignore);
    $(document).on("click", ".task_reject", window.render.tasks_reject);

    $(document).on({
        mouseenter: function () {
            $("#task_btn_group").toggleClass("uk-hidden");
        },
        mouseleave: function () {
            $("#task_btn_group").toggleClass("uk-hidden");
        }
    }, "#tasks_info");


})(window, document, jQuery);