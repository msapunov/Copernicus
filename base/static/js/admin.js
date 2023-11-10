(function(window, document, $, undefined){
    "use strict";
    window.admin = {};


    window.admin.tasks_btn_toggle = function(){
        var tid = $(this).data("tid");
        $(".task_btn_" + tid).prop("disabled", false);
    };
    window.admin.tasks_sel_update = function(){
        var data = $(this).data("id");
        var selectors = $("#"+data).find("select");
        $.each(selectors, function(idx, el){
            var val = $(el).attr("data-val");
            if(val != "") {
                $(el).val(val);
            }
        });
    };
    window.admin.tasks_act=function(action, btn){
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
    window.admin.tasks_accept=function(){
        window.admin.tasks_act("accept", this);
    };
    window.admin.tasks_ignore=function(){
        window.admin.tasks_act("ignore", this);
    };
    window.admin.tasks_reject=function(){
        window.admin.tasks_act("reject", this);
    };
    window.admin.tasks_manage = function(){
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
                    table.append(window.admin.render_task(val, false));
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
    window.admin.tasks_btn_toggle = function(){
        var tid = $(this).data("tid");
        $(".task_btn_" + tid).prop("disabled", false);
    };
    window.admin.tasks_edit = function(){
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
            var icon = window.admin.decision_icon(data.data.decision);
            deci.html(icon.prop("outerHTML"));
        });
    };
    window.admin.tasks_history = function(){
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
                    table.append(window.admin.render_task(val, true));
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
    window.admin.task_hidden_row = function(val){

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
    window.admin.task_row = function(val){
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
    window.admin.tasks_reload=function(){
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
    window.admin.new_project=function(){
        var data = $(this).data("id");
        $("#"+data).toggleClass("uk-hidden");
        $(this).closest("tr").eq(0).toggleClass("ext_info");
        $(this).find("span").eq(0).toggleClass("uk-icon-plus uk-icon-minus");
    };
    window.admin.render_manage = function(val){
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
    window.admin.render_task_item = function(val){
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
    window.admin.decision_icon = function(decision){
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
    window.admin.render_task = function(val, item){
        var icon = window.admin.decision_icon(val.decision);

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
            var td_hdn = window.admin.render_task_item(val);
        }else{
            var td_hdn = window.admin.render_manage(val);
        }

        var tr_hdn = $("<tr/>").attr({"id": "history-"+val.id});
        tr_hdn.addClass("ext_info uk-hidden");
        tr_hdn.append(td_hdn);
        return tr.add(tr_hdn);
    };
    window.admin.tasks = function(){
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

                    var row = window.admin.task_row(val);
                    var hidden = window.admin.task_hidden_row(val);

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
                    window.admin.tasks_reload();
                    modal.off('hide.uk.modal');
                }});

            }
        });
    };

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
        partition: "admin/partition/info",
        space: "admin/space/info",
        system: "admin/sys/info",
        pending: "admin/pending/list",
        tasks: "admin/tasks/list",
        tasks_accept: "admin/tasks/accept",
        tasks_history: "admin/tasks/history",
        tasks_ignore: "admin/tasks/ignore",
        tasks_reject: "admin/tasks/reject",
        tasks_update: "admin/tasks/update",
        expand_pending: "admin/bits/pending",
        user: "admin/user/info",
        visa: "admin/registration/visa",
        visa_resend: "admin/registration/visa/resend"
    };
    window.admin.submit = function (){
        let table = $('table#pending_projects').DataTable();
        let rows = table.rows('.shown').ids();
        submit.call(this).done(function(data){
            table.ajax.reload(function () {
                for(var i = 0; i < rows.length; i++){
                    let el = $('#' + rows[i] + ' td.details-control');
                    if (el.length > 0) {
                        el.click();
                    };
                }
            });
        });
    };
    window.admin.expand_processing = function(tr, tdi, show){
        if(show === true){
            tr.removeClass('shown');
            tdi.first().removeClass('uk-icon-minus');
            tdi.first().removeClass('uk-icon-spin');
            tdi.first().addClass('uk-icon-plus');
        }else if(show === false){
            tr.addClass('shown');
            tdi.first().removeClass('uk-icon-plus');
            tdi.first().removeClass('uk-icon-spin');
            tdi.first().addClass('uk-icon-minus');
        }else if(show === undefined){
            tdi.first().removeClass('uk-icon-minus');
            tdi.first().removeClass('uk-icon-plus');
            tdi.first().addClass('uk-icon-spin');
        }
    };
    window.admin.expand = function format(d, row, tr, tdi){
            // `d` is the original data object for the row
            let id = row.id();
            let url = "{0}/{1}".f(window.admin.url.expand_pending, id);
            window.admin.expand_processing(tr, tdi);
            ajax(url).done(function(data){
                row.child(data).show();
                window.admin.expand_processing(tr, tdi, false);
            }).fail(function(){
                window.admin.expand_processing(tr, tdi, true);
            });
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
        $("#system").DataTable({
            ajax: {type: "POST", url: window.admin.url.system},
            dom: 'tiB',
            buttons: {
                className: 'copyButton',
                buttons: [ 'refresh' ]
            },
            paging: false,
            searching: false,
            columns: [{
                data: "server"
            },{
                data: "memory",
            },{
                data: "swap",
            },{
                data: "load"
            },{
                data: "uptime"
            }],
            rowCallback: function(row_html, data) {
                if("html" in data){
                    let row = $("#system").DataTable().row(row_html);
                    row.child(data.html).show();
                }
            }
        });
        $("#disk_space").DataTable({
            ajax: {type: "POST", url: window.admin.url.space},
            dom: 'tiB',
            buttons: {
                className: 'copyButton',
                buttons: [ 'refresh' ]
            },
            paging: false,
            searching: false,
            columns: [
                {data: "mountpoint"},
                {data: "size"},
                {data: "used"},
                {data: "available"},
                {data: "use"},
                {data: "filesystem"}
            ]
        });
        $("#sinfo").DataTable({
            ajax: {"type": "POST", "url": window.admin.url.sinfo},
            dom: 'tiB',
            buttons: {
                className: 'copyButton',
                buttons: [ 'refresh' ]
            },
            paging: false,
            searching: false,
            columns: [{
                data: "node"
            },{
                className: "dt-body-nowrap",
                data: "reason"
            },{
                data: "date",
                render: function ( date, type, row ) {
                    let dateSplit = date.split(' ');
                    let full = row.date_full
                    return type === "display" || type === "filter" ? '<div title="' + full + '">' + dateSplit[0] : date;
                }
            },{
                data: "status"
            }]
        });
        $("#overview").DataTable({
            ajax: {type: "POST", url: window.admin.url.partition},
            dom: 'tiB',
            buttons: {
                className: 'copyButton',
                buttons: [ 'refresh' ]
            },
            paging: false,
            searching: false,
            columns: [
                {data: "name"},
                {data: "allocated"},
                {data: "idle"},
                {data: "other"},
                {data: "total"}
            ]
        });
        $("#pending_projects").DataTable({
            ajax: {"type": "POST", "url": window.admin.url.pending},
            dom: 'tiB',
            buttons: {
                className: 'copyButton',
                buttons: [ 'refresh' ]
            },
            rowId: 'id',
            paging: false,
            searching: false,
            columns: [{
                className: 'details-control',
                orderable: false,
                data: null,
                defaultContent: '',
                render: function () {
                    return '<span class="btn uk-icon-plus"></span>';
                },
                width:"15px"
            },{
                data: "type",
                render: function (data, type, row) {
                    if ( "A" === data ){
                        return '<span class="uk-text-bold uk-text-success">A</span>'
                    } else if( "B" === data ){
                        return '<span class="uk-text-bold uk-text-primary">B</span>'
                    } else if( "C" === data ){
                        return '<span class="uk-text-bold uk-text-danger">C</span>'
                    } else if( "E" === data ){
                        return '<span>E</span>'
                    } else if( "H" === data ){
                        return '<span class="uk-text-bold uk-text-warning">H</span>'
                    }else{
                        return '<span>'+data+'</span>'
                    }
                },
                width:"20px"
            },{
                data: "title"
            },{
                data: "responsible_full_name",
                render: function ( data ) {
                    return '<span class="uk-text-nowrap">' + data + '</span>';
                }
            },{
                data: "cpu",
                render: $.fn.dataTable.render.number( '.', '')
            },{
                data: "ts",
                render: function ( date, type, row ) {
                    let dateSplit = date.split(' ');
                    let full = row.ts_full
                    return type === "display" || type === "filter" ? '<div title="' + full + '">' + dateSplit[0] : date;
                }
            },{
                className: 'pending_info',
                orderable: false,
                data: null,
                defaultContent: '',
                render: function ( data, type, row ) {
                    let status = (row.status) ? row.status.toUpperCase() : "NONE";
                    if ( "APPROVED" === status ) {
                        return '<span class="uk-icon-wrench uk-text-danger" title="Request status: '+status+'"></span>';
                    }else if ( "VISA SENT" === status ) {
                        if ( data.visa_expired == true){
                            return '<span class="uk-icon-exclamation-circle uk-text-danger" title="Request status: '+status+'"></span>';
                        }else {
                            return '<span class="uk-icon-edit uk-text-warning" title="Request status: '+status+'"></span>';
                        }
                    }else if ( "VISA RECEIVED" === status ) {
                        return '<span class="uk-icon-check uk-text-success" title="Request status: '+status+'"></span>';
                    }else if ( "VISA SKIPPED" === status ) {
                        return '<span class="uk-icon-check uk-text-success" title="Request status: '+status+'"></span>';
                    }else{
                        return '<span class="uk-icon-question uk-text-primary" title="Request status: '+status+'"></span>';
                    }
                },
                width:"20px"
            }]
        });
        $('#pending_projects tbody').on('click', 'td.details-control', function () {
            let tr = $(this).closest('tr');
            let tdi = tr.find("span.btn");
            let row = $('#pending_projects').DataTable().row(tr);
            if (row.child.isShown()) {
                row.child.hide();
                window.admin.expand_processing(tr, tdi, true);
            }else {
                window.admin.expand(row.data(), row, tr, tdi);
            }
        });

        $(document).on("click", ".window_hide", trigger_modal);

        $(document).on("click", ".pending_create", trigger_modal);
        $(document).on("click", ".pending_create_submit", window.admin.submit);
        $(document).on("click", ".pending_received", trigger_modal);
        $(document).on("click", ".pending_received_submit", window.admin.submit);
        $(document).on("click", ".pending_visa", trigger_modal);
        $(document).on("click", ".pending_visa_submit", window.admin.submit);
        $(document).on("click", ".pending_approve", trigger_modal);
        $(document).on("click", ".pending_approve_submit", window.admin.submit);

        $(document).on("click", ".edit_info", trigger_modal);
        $(document).on("click", ".edit_info_submit", window.admin.submit);
        $(document).on("click", ".edit_responsible", trigger_modal);
        $(document).on("click", ".edit_responsible_submit", window.admin.submit);
        $(document).on("click", ".edit_users", trigger_modal);
        $(document).on("click", ".edit_users_submit",  window.admin.submit);
        $(document).on("click", ".edit_new", trigger_modal);
        $(document).on("click", ".edit_new_submit", window.admin.submit);

        $(document).on("click", ".pending_message", trigger_modal);
        $(document).on("click", ".pending_message_submit", window.admin.submit);

        $(document).on("click", ".pending_reset", trigger_modal);
        $(document).on("click", ".pending_reset_submit", window.admin.submit);
        $(document).on("click", ".pending_ignore", trigger_modal);
        $(document).on("click", ".pending_ignore_submit", window.admin.submit);
        $(document).on("click", ".pending_reject", trigger_modal);
        $(document).on("click", ".pending_reject_submit", window.admin.submit);

    $(document).on("click", ".task_show", window.admin.tasks);
    $(document).on("click", ".task_info", window.admin.new_project);
    $(document).on("click", ".task_history", window.admin.tasks_history);
    $(document).on("click", ".task_manage", window.admin.tasks_manage);
    $(document).on("click", ".task_reload", window.admin.tasks_reload);
    $(document).on("click", ".task_accept", window.admin.tasks_accept);
    $(document).on("click", ".task_ignore", window.admin.tasks_ignore);
    $(document).on("click", ".task_reject", window.admin.tasks_reject);
    $(document).on("click", ".task_edit", window.admin.tasks_edit);
    $(document).on("click", ".history_info", window.admin.new_project);
    $(document).on("click", ".history_info", window.admin.tasks_sel_update);
    $(document).on("change", ".task_sel_info", window.admin.tasks_btn_toggle);
        $(document).on({
            mouseenter: function () {
                $("#task_btn_group").toggleClass("uk-hidden");
            },
            mouseleave: function () {
                $("#task_btn_group").toggleClass("uk-hidden");
            }
        }, "#tasks_info");
    });
})(window, document, jQuery);
