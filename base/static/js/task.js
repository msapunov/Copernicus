(function(window, document, $, undefined){
    "use strict";
    window.task = {};
    window.task.url = {
        details: "admin/tasks/info",
        list: "/admin/tasks/history"
    };
    window.task.submit = function (){
        let table = $('table#tasks').DataTable();
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
    window.task.status = function status(btn, table){
        if(!$(btn).hasClass("uk-active")){
            return;
        }
        const state = $.trim( $(btn).data("status") );
        if( state === "waiting") {
            table.column(4).search('^$', true, false).draw();
        } else if( state === "processed"){
            table.column(4).search("processed").draw();
            $.fn.dataTable.ext.search.push(
                function(settings, data, dataIndex) {
                    let originalData = table.cell(dataIndex, 5).data();
                    return originalData === "accept";
                }
            );
            table.draw();
            $.fn.dataTable.ext.search.pop();
        }else{
            table.column(4).search(state).draw();
        }
    };
    window.task.items = function project_state(btn, table){
        if(!$(btn).hasClass("uk-active")){
            return;
        }
        let items = $.trim( $(btn).data("items") );
        table.page.len( items ).draw();
    };
    window.task.expand_processing = function(tr, tdi, show){
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
    window.task.expand = function format(d, row, tr, tdi){
            // `d` is the original data object for the row
            let id = d.id;
            let url = "{0}/{1}".f(window.task.url.details, id);
            window.task.expand_processing(tr, tdi);
            ajax(url).done(function(data){
                row.child("<div class='uk-grid'>" + data + "</div>").show();
                window.task.expand_processing(tr, tdi, false);
            }).fail(function(request){
                window.task.expand_processing(tr, tdi, true);
            });
    };
    $(document).on("ready", function(){
        let table = $("#tasks").DataTable({
            ajax: {type: "POST", url: window.task.url.list},
            dom: "tip",
            pageLength: 100,
            columns: [{
                className: 'details-control',
                orderable: false,
                data: "id",
                defaultContent: '',
                render: function () {
                    return '<span class="btn uk-icon-plus"></span>';
                },
                width:"15px"
            },{
                data: "action"
            },{
                data: "created",
                render: function ( date, type, row ) {
                    let dateSplit = date.split(' ');
                    let full = row.date_full
                    return type === "display" || type === "filter" ? '<div title="' + date + '">' + dateSplit[0] : date;
                }
            },{
                data: "author"
            },{
                data: "status"
            },{
                data: "decision",
                searchable: false,
                render: function ( data, type, row ) {
                    if(data === "accept"){
                        return '<span class="uk-icon-thumbs-o-up" title="accepted"></span>';
                    }else if(data === "ignore"){
                        return '<span class="uk-icon-thumbs-o-down" title="ignored"></span>';
                    }else if(data === "reject"){
                        return '<span class="uk-icon-thumbs-down" title="rejected"></span>';
                    }else{
                        return '';
                    }
                },
                width:"15px"
            },{
                data: "description",
                visible: false
            }]
        });
        $('#tasks tbody').on('click', 'td.details-control', function () {
            let tr = $(this).closest('tr');
            let tdi = tr.find("span.btn");
            let row = table.row(tr);
            if (row.child.isShown()) {
                row.child.hide();
                window.task.expand_processing(tr, tdi, true);
            }else {
                window.task.expand(row.data(), row, tr, tdi);
            }
        });
        $("#table_search").on( "keyup", function () {
            table.search( this.value ).draw();
        });
        $(document).on("click", ".window_hide", trigger_modal);

        $(document).on("click", ".items", function(){ window.task.items(this, table) });
        $(document).on("click", ".task-status", function(){ window.task.status(this, table) });

        $(document).on("click", ".accept", trigger_modal);
        $(document).on("click", ".accept_submit", window.task.submit);

        $(document).on("click", ".ignore", trigger_modal);
        $(document).on("click", ".ignore_submit", window.task.submit);

        $(document).on("click", ".reject", trigger_modal);
        $(document).on("click", ".reject_submit", window.task.submit);

        $(document).on("click", ".edit", trigger_modal);
        $(document).on("click", ".edit_submit", window.task.submit);
    });
})(window, document, jQuery);