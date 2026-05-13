(function(window, document, $, undefined){
    "use strict";
    window.registry = {};
    window.registry.url = {
        expand_user: "admin/bits/user_info",
    };
    window.registry.expand_processing = function(tr, tdi, show){
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
    window.registry.expand = function format(d, row, tr, tdi){
            // `d` is the original data object for the row
            let id = d.login;
            let url = "{0}/{1}".f(window.registry.url.expand_user, id);
            window.registry.expand_processing(tr, tdi);
            ajax(url).done(function(data){
                row.child("<div class='uk-grid'>" + data + "</div>").show();
                window.registry.expand_processing(tr, tdi, false);
            }).fail(function(request){
                window.registry.expand_processing(tr, tdi, true);
            });
    };
    window.registry.user_status = function project_state(btn, table){
        if(!$(btn).hasClass("uk-active")){
            return;
        }
        const status = $.trim( $(btn).data("status") );
        table.column(2).search(status).draw();
        if(status === ""){
            table.column(1).visible(true);
        }else{
            table.column(1).visible(false);
        }
    };
    window.registry.acl_type = function project_state(btn, table){
        if(!$(btn).hasClass("uk-active")){
            return;
        }
        let columns = [];
        let column_n = $.trim( $(btn).data("type") );
        $(".acl-type").each(function() {
            let idx = $(this).data("type");
            columns.push(idx);
        });
        if(column_n == ""){
            table.columns(columns).search("").draw();
        }else{
            column_n = (column_n/1);
            table.columns(columns).search("");
            table.columns(column_n).search("True").draw();
        }
    };
    window.registry.update_projects = function update_projects(select){
        const login = $.trim( $(select).data("user") );
        const id = "#" + login + "_selected_projects";
        const values = $(select).val();
        var text = "None";
        if(values.length > 0){
            text = values.join(", ");
        }
        $(id).text(text);
    };
    window.registry.dump = function dump(type, e){
        if(!type in ["csv", "ods", "xls"]){
            e.preventDefault();
            alert("Extension " + type + " is not supported");
            return;
        }
        let data = $("#statistics").DataTable().rows({search:'applied'}).data().toArray();
        if(data.length < 1){
            e.preventDefault();
            alert("No records to save, table is empty!");
            return;
        }
        let pid=[];
        data.forEach(function(row) {
            pid.push(row.name);
        });

        let url = "projects." + type + "?projects=" + pid.join(",");
        let id = ".dump_" + type;
        let anchor = $(id);
        anchor.attr("href", url);
    };
    $(document).on("ready", function(){
        let table = $("#registry").DataTable({
            //dom: "tip",
            dom: 'tip',
            buttons: [{
                    extend: 'csvHtml5',
                    title: 'DataExport',
                    exportOptions: {
                        columns: ':not(.noExport)'
                    },
                    className: 'dump_csv'
                },{
                    extend: 'excelHtml5',
                    title: 'DataExport',
                    exportOptions: {
                        columns: ':not(.noExport)'
                    },
                    className: 'dump_xls'
            }],
            pageLength: 100,
            rowCallback: function (row, data) {
                if (data.status === "archived") {
                    $('td', row).each(function(index) {
                        if(index > 0){
                            $(this).addClass("uk-text-muted");
                        }
                    });
                }
            },
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
                className: 'uk-text-center',
                data: "status",
                render: function ( date, type, row ) {
                    return row.status === "active" ? '<span class="btn uk-icon-check"></span>' : '';
                }
            },{
                data: "status",
                visible: false
            },{
                data: "login"
            },{
                data: "name",
                render: function ( text ) {
                    return '<span class="uk-text-capitalize">' + text + '</span>';
                }
            },{
                data: "surname",
                render: function ( text ) {
                    return '<span class="uk-text-capitalize">' + text + '</span>';
                }
            },{
                data: "email",
                visible: false
            },{
                data: "seen",
                render: function ( date, type, row ) {
                    let dateSplit = date.split(' ');
                    let full = row.seen;
                    return type === "display" || type === "filter" ? '<div title="' + full + '">' + dateSplit[0] : date;
                }
            },{
                className: 'uk-text-center',
                data: "user",
                render: function ( date, type, row ) {
                    return row.user === "True" ? '<span class="btn uk-icon-check"></span>' : '';
                }
            },{
                data: "user",
                visible: false
            },{
                className: 'uk-text-center',
                data: "responsible",
                render: function ( date, type, row ) {
                    return row.responsible === "True" ? '<span class="btn uk-icon-check"></span>' : '';
                }
            },{
                data: "responsible",
                visible: false
            },{
                className: 'uk-text-center',
                data: "manager",
                render: function ( date, type, row ) {
                    return row.manager === "True" ? '<span class="btn uk-icon-check"></span>' : '';
                }
            },{
                data: "manager",
                visible: false
            },{
                className: 'uk-text-center',
                data: "tech",
                render: function ( date, type, row ) {
                    return row.tech === "True" ? '<span class="btn uk-icon-check"></span>' : '';
                }
            },{
                data: "tech",
                visible: false
            },{
                className: 'uk-text-center',
                data: "committee",
                render: function ( date, type, row ) {
                    return row.committee === "True" ? '<span class="btn uk-icon-check"></span>' : '';
                }
            },{
                data: "committee",
                visible: false
            },{
                className: 'uk-text-center',
                data: "admin",
                render: function ( date, type, row ) {
                    return row.admin === "True" ? '<span class="btn uk-icon-check"></span>' : '';
                }
            },{
                data: "admin",
                visible: false
            }]
        });
        $('#registry tbody').on('click', 'td.details-control', function () {
            let tr = $(this).closest('tr');
            let tdi = tr.find("span.btn");
            let row = table.row(tr);
            if (row.child.isShown()) {
                // This row is already open - close it
                row.child.hide();
                window.registry.expand_processing(tr, tdi, true);
            }else {
                // Open row in ajax callback in function window.registry.expand
                window.registry.expand(row.data(), row, tr, tdi);
            }
        });
        $("#table_search").on( "keyup", function () {
            table.search( this.value ).draw();
        });
        $(document).on("click", ".contact", trigger_modal);
        $(document).on("click", ".message_submit", submit);
        $(document).on("click", ".edit_submit", submit);
        $(document).on("click", ".ed_mail", trigger_modal);
        $(document).on("click", ".user_activate", trigger_modal);
        $(document).on("click", ".user_add", trigger_modal);
        $(document).on("click", ".set", trigger_modal);
        $(document).on("click", ".reset", trigger_modal);
        $(document).on("click", ".welcome", trigger_modal);
        $(document).on("click", ".set_submit", submit);
        $(document).on("click", ".reset_submit", submit);
        $(document).on("click", ".welcome_submit", submit);
        $(document).on("click", ".dump_csv", function(e){e.preventDefault(); table.button('.dump_csv').trigger(); });
        $(document).on("click", ".dump_xls", function(e){e.preventDefault(); table.button('.dump_xls').trigger(); });
        $(document).on("change", ".project_select", function(){ window.registry.update_projects(this) });
        $(document).on("click", ".user-status", function(){ window.registry.user_status(this, table) });
        $(document).on("click", ".acl-type", function(){ window.registry.acl_type(this, table) });
        $(document).on("click", ".window_hide", trigger_modal);
        $(document).on("click", ".user_activate", function () {
            window.registry.update_projects(this)
        });
    });
})(window, document, jQuery);