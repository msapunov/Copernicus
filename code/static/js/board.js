(function(window, document, $, undefined){
    "use strict";
    window.contact = "mesocentre-techn@univ-amu.fr";
    window.board = {};
    window.board.url = {
        list: "board/list",
        accept: "board/accept",
        reject: "board/reject",
        ignore: "board/ignore",
        activate: "board/activate",
        transform: "board/transform",
        history: "project/history"
    };
    window.board.id = "#ext_result_table";
    window.board.visible = [];
    window.board.column = [
        {data: null, defaultContent: ""},
        {data: "project_name"},
        {data: "responsible"},
        {data: "total"},
        {data: "use"},
        {data: "hours"},
        {data: "activate"},
        {data: "activate"},
        {data: "transform"},
        {data: "transform"},
        {data: "created"},
        {data: "reason"},
        {data: "id"},
        {data: "pid"},
        {data: "used"},
        {data: "responsible_login"},
    ];
    window.board.def = [{
        className: "ctrl",
        orderable: false,
        targets: 0,
        render: function(data, type, full, meta){
            return window.render.button("plus").data("data", data).prop("outerHTML");
        }
    },{
        "visible": false,  "targets": [7, 9, 11, 12, 13, 14, 15]
    },{
        targets: 5,
        render: function(data, type, full, meta){
            if(data>0){
                return data;
            }else{
                return "";
            }
        }
    },{
        targets: 6,
        orderData: 7,
        render: function(data, type, full, meta){
            if(data=="True"){
                return window.icon("check");
            }else{
                return "";
            }
        }
    },{
        targets: 8,
        orderData: 9,
        render: function(data, type, full, meta){
            if(data=="True"){
                return window.icon("check");
            }else{
                return "";
            }
        }
    },{
        targets: 10,
        render: function(data, type, full, meta){
            var date = full.created;
            return moment(data, "X").format("YYYY-MM-DD HH:mm");
        }
    }];

    window.board.order = [[10, "desc"]];
    window.board.responsive = {details: {type: ""}};
    window.board.init = function(){
        window.board.table = $(window.board.id).DataTable({
            columns: window.board.column,
            columnDefs: window.board.def,
            order: window.board.order,
            responsive: true,
            sDom: "t", // remove all the pagination buttons and elements
        });
    };

    window.board.send = function(url, data){
        var modal = UIkit.modal.blockUI("Sending data...");
        return $.ajax({
            contentType: "application/json",
            data: JSON.stringify(data),
            dataType: "json",
            timeout: 5000,
            type: "POST",
            url: window.board.url[url]
        }).done(function(resp){
            UIkit.notify("Data exchange finished successfully", {timeout: 2000, status:"success"});
        }).fail(function(request){
            window.error(request);
        }).always(function() {
            modal.hide();
        });
    }

    window.icon = function(css){
        return $("<span/>").attr({
            "class": "uk-icon-{0}".f(css),
            "aria-hidden": "true"
        }).prop("outerHTML");
    }

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
    window.render.li = function(title, data){
        title = $("<span/>")
            .css("font-weight", "bold")
            .attr({"class": "dtr-title"})
            .html(title.capitalize() + ": ");
        data = $("<span/>").attr({"class": "dtr-data"}).html(data);
        return $("<li/>").append(title, data);
    }

    window.render.button = function(mode){
        var button = $("<button>").attr({"class": "uk-button"});
        var icon = "question";
        if(mode == "accept"){
            icon = "thumbs-up";
            button.addClass("accept");
        }else if(mode == "reject"){
            icon = "thumbs-down";
            button.addClass("uk-button-danger reject");
        }else if(mode == "ignore"){
            icon = "thumbs-o-down";
            button.addClass("ignore");
        }else if(mode == "plus"){
            icon = "plus";
            button.addClass("ext_row uk-button-mini");
        }else if(mode == "contact"){
            icon = "commenting";
            button.addClass("contact");
        }else if(mode == "history"){
            icon = "history";
            button.addClass("history");
        }
        if(mode != "plus"){
            return button.html(window.icon(icon) + " " + mode.capitalize());
        }else{
            return button.html(window.icon(icon));
        }
    }

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
        window.board.kill("ignore", me)
    }

    window.board.reject = function(){
        var me = this;
        window.board.kill("reject", me)
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
        var id = $(this).data("id");
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
        $(rid).empty();
        $(rid_info).empty();
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

    window.render.info = function(el, data){
        var columns = window.board.table.settings().init().columns;
        var div = $("<div/>").attr({"class": "uk-clearfix"});
        var ul = $("<ul/>").appendTo(div);
        el.children().filter(":hidden").each(function(){
            var idx = window.board.table.cell(this).index().column;
            var info = window.board.table.cell(this).data();
            var title = columns[idx].data;
            (window.render.li(title, info)).appendTo(ul);
        });
        (window.render.li("CPU total", data.total)).appendTo(ul);
        (window.render.li("CPU used", data.used)).appendTo(ul);
        (window.render.li("CPU usage", data.use)).appendTo(ul);
        (window.render.li("comments", data.reason)).appendTo(ul);

        var group = $("<div/>").attr({"class": "uk-button-group uk-float-right"});

        if(!data.processed){
            window.render.button("accept").data("data", data).appendTo(group);
            window.render.button("ignore").data("data", data).appendTo(group);
            window.render.button("reject").data("data", data).appendTo(group);
        }
        group.appendTo(div);

        var history = $("<div/>").attr({"class": "uk-button-group uk-float-left"});
        window.render.button("history").data("data", data).appendTo(history);
        window.render.button("contact").data("data", data).appendTo(history);
        history.appendTo(div);
        return div
    }

    window.render.redraw = function(e, dt, columns){
        dt.rows().every(function(rIndex, tLoop, rLoop){
            var child = this.child();
            if(!child) return false;
            var ul = child.find("ul");
            var data = this.data();
            var ctitle = dt.settings().init().columns;
            ul.empty();
            columns.forEach(function(value, idx){
                var title = ctitle[idx].data;
                if(value === false){
                    ul.append(window.render.li(title, data[title]));
                }
            });
            (board.responsive.render("comments", data.reason)).appendTo(ul);
            var colspan = columns.reduce(function(a, b){
                return b === true ? a+1 : a;
            }, 0);
            child.find("td").eq(0).attr("colspan", colspan);
        });
    }

    window.render.expand = function(e, dt, indexes){
        if(e.target !== this) return;

        var btn = $(this);
        var tr = btn.closest("tr");
        var row = window.board.table.row(tr);

        if(row.child.isShown()){  // This row is already open - close it
            row.child.hide();
            tr.removeClass("ext_info");
            btn.toggleClass("glyphicon-minus glyphicon-plus");
        }else{  // Open this row
            window.board.table.rows().every(function(rIndex, tLoop, rLoop){  // Close other rows
                if (! this.child()) return false;
                this.child.hide();
                var tmp = this.node();
                $(tmp).removeClass("ext_info");
                $(tmp).find(".glyphicon-minus").toggleClass("glyphicon-minus glyphicon-plus");
            });
            row.child( window.render.info(tr, row.data()), "ext_info").show();
            tr.addClass("ext_info");
            btn.toggleClass("glyphicon-plus glyphicon-minus");
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

    $(document).on("ready", window.board.init);
    $(document).on("click", ".new_ext", window.render.new_extension);
    $(document).on("click", ".history", window.board.history);
    $(document).on("click", ".accept", window.board.accept);
    $(document).on("click", ".reject", window.board.reject);
    $(document).on("click", ".ignore", window.board.ignore);
    $(document).on("click", ".contact", window.board.message);

    $(window.board.id).on("responsive-resize.dt", window.render.redraw);

})(window, document, jQuery);