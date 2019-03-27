(function(window, document, $, undefined){
    "use strict";
    window.board = {};
    window.board.url = {
        list: "board/list",
        accept: "board/accept",
        reject: "board/reject",
        ignore: "board/ignore",
        activate: "board/activate",
        transform: "board/transform",
        history: "project/history",
        global_history: "board/history"
    };

    window.render = {};

    window.board.accept = function(e){
        var me = this;
        var id = $(me).data("id");
        var project = $(me).data("name");
        var act = $(me).data("act");
        var trans = $(me).data("trans");
        if(trans=="True"){
            return window.board.transform(me)
        }else if(act=="True"){
            return window.board.activate(me)
        }else{
            return window.board.extend(me)
        }
    }

    window.board.transform = function(me){
        var id = $(me).data("id");
        var project = $(me).data("name");
        var title = "Accept transformation of project {0} to type B?".f(project);
        var text = "Transformation accepted by scientific committee";
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
            json_send(window.board.url.transform, {
                "eid": id,
                "comment": comment
            }).done(function(reply){
                window.process(reply);
            });
        });
    }

    window.board.activate = function(me){
        var id = $(me).data("id");
        var project = $(me).data("name");
        var title = "Accept activation of project {0}?".f(project);
        var text = "Activation accepted by scientific committee";
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
            json_send(window.board.url.activate, {
                "eid": id,
                "comment": comment
            }).done(function(reply){
                window.process(reply);
            });
        });
    }

    window.board.extend = function(me){
        var id = $(me).data("id");
        var project = $(me).data("name");
        var hours = $(me).data("cpu");
        var title = "Accept extension of project {0} by {1} hours?".f(project, hours);
        var text = "Extension accepted by scientific committee";
        var cpu = $("<input/>").addClass("uk-width-1-1").attr({
            "name": "cpu",
            "type": "text",
            "value": hours
        });
        var motiv = $("<textarea/>").html(text).addClass("uk-width-1-1").attr({
            "rows": "4",
            "name": "note"
        });
        var form = $("<form/>").addClass("uk-form").append(
                $("<legend/>").text(title)
            ).append(
                $("<div/>").addClass("uk-form-row").append(cpu)
            ).append(
                $("<div/>").addClass("uk-form-row").append(motiv)
            );
        UIkit.modal.confirm(form.prop("outerHTML"), function(){
            var comment = $("textarea[name=note]").val();
            var cpu_hours = $("input[name=cpu]").val();
            json_send(window.board.url.accept, {
                "eid": id,
                "comment": comment,
                "cpu": cpu_hours
            }).done(function(reply){
                window.process(reply);
            });
        });
    }

    window.board.ignore = function(){
        var me = this;
        window.board.kill(window.board.url.ignore, me)
    }

    window.board.reject = function(){
        var me = this;
        window.board.kill(window.board.url.reject, me)
    }
    window.board.kill = function(url_name, me){
        if (typeof(url_name)==="undefined") url_name="reject";
        if (typeof(me)==="undefined") me=this;

        var id = $(me).data("id");
        var project = $(me).data("name");
        var act = $(me).data("act");
        var trans = $(me).data("trans");

        if(act=="True"){
            var action = "activation";
        }else if(trans=="True"){
            var action = "transformation";
        }else{
            var action = "extension";
        }
        if(url_name=="ignore"){
            var verb = "ignoring";
        }else{
            var verb = "rejecting";
        }
        var title = "{0} {1} of project {2}".f(verb.capitalize(), action, project);
        var text = "Enter a reason for {0} {1} of project {2}".f(verb, action, project);
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
            json_send(url_name, {
                "eid": id,
                "comment": comment
            }).done(function(reply){
                window.process(reply);
            });
        });
    }

    window.board.history = function(){
        var id = $(this).data("pid");
        var name = $(this).data("name");
        var title = "History for project {0}".f(name);
        json_send(window.board.url.history, {"project": id}).done(function(reply){
            if(reply.length > 0){
                window.render.history(reply, title);
            }else{
                UIkit.modal.alert("No history found for project {0}".f(name));
            }
        });
    }

    window.process = function(record){
        if(record.message){
            UIkit.notify(record.message, {timeout: 2000, status:"success"});
        }
        if(!record.data.id){
            alert("Returned record has no ID");
        };
        var rid = "#" + record.data.id;
        var rid_info = rid+"-info";
        $(rid).remove();
        $(rid_info).remove();
        var recs = $("#ext_result_records").find("tr");
        if(recs.length < 1){
            $("#ext_projects_table").remove();
            $(".treated").toggleClass("uk-hidden");
        }
    }

    window.render.history = function(data, title){
        var info = $("<table/>").addClass(
            "uk-table uk-table-striped uk-table-condensed");
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
    }

    window.board.message = function(){
        var login = $(this).data("login");
        message_window([login]);
    }

    window.render.new_extension = function(){
        var data = $(this).data("id");
        $("#"+data).toggleClass("uk-hidden");
        $(this).closest("tr").eq(0).toggleClass("ext_info");
        $(this).find("span").eq(0).toggleClass("uk-icon-plus uk-icon-minus");
    }

    $(document).on("click", ".new_ext", window.render.new_extension);
    $(document).on("click", ".history", window.board.history);
    $(document).on("click", ".accept", window.board.accept);
    $(document).on("click", ".reject", window.board.reject);
    $(document).on("click", ".ignore", window.board.ignore);
    $(document).on("click", ".contact", window.board.message);
    $(document).on("click", ".global_history", window.board.global_history);

})(window, document, jQuery);