(function(window, document, $, undefined){
    "use strict";
    window.admin = {};

    window.admin.url = {
        info: "admin/partition/info",
        history: "admin/history",
        message: "admin/message/register",
        sinfo: "admin/slurm/nodes/list",
        partition: "admin/partition/info",
        space: "admin/space/info",
        system: "admin/sys/info",
        pending: "admin/pending/list",
        accounting: "admin/accounting/365",
        tasks: "admin/tasks/list",
        tasks_accept: "admin/tasks/accept",
        tasks_history: "admin/tasks/history",
        tasks_ignore: "admin/tasks/ignore",
        tasks_reject: "admin/tasks/reject",
        tasks_update: "admin/tasks/update",
        expand_pending: "admin/bits/pending",
        user: "admin/user/info"
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
    window.admin.task_submit = function (){
        submit.call(this).done(function(data){
            if(data.html){
                $('#tasks_to_process').replaceWith(data.html);
            }
            if(data.info){
                UIkit.notify(data.info, {status:'success'});
            }
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
        $.ajax({
            type: "POST",
            url: window.admin.url.accounting
        }).done(function(reply){
            accounting("accounting", reply, 100);
        });
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
                data: "server",
                render: function(data, type, row) {
                    return '<div title="' + data + '" style="white-space: nowrap;">' + data + '</div>';
                }
            },{
                data: "memory"
            },{
                data: "swap"
            },{
                data: "load"
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
                        if ( data.visa_expired === true){
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

        $(document).on("click", ".task_show", trigger_modal);
        $(document).on("click", ".task_accept_submit", window.admin.task_submit);
        $(document).on("click", ".task_ignore_submit", window.admin.task_submit);
        $(document).on("click", ".task_reject_submit", window.admin.task_submit);
        $(document).on({
            mouseenter: function () {
                $("#task_btn_group").toggleClass("uk-hidden");
            },
            mouseleave: function () {
                $("#task_btn_group").toggleClass("uk-hidden");
            }
        }, "#tasks_info");
        setInterval(function(){
            $.ajax({
                timeout: 60000,
                type: "POST",
                url: window.admin.url.accounting
            }).done(function(data){
                accounting("accounting", data, 100);
            });
        }, 86400000);
        setInterval(function(){
            $.ajax({
                timeout: 60000,
                type: "POST",
                url: window.admin.url.tasks
            }).done(function(data){
                $("#taks_queue_length").text(data.data.length);
            });
        }, 60000);
    });
})(window, document, jQuery);
