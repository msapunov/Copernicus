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
                row.child(data).show();
                window.registry.expand_processing(tr, tdi, false);
            }).fail(function(request){
                window.registry.expand_processing(tr, tdi, true);
            });
    };
    window.registry.user_status = function project_state(btn, table){
        if(!$(btn).hasClass("uk-active")){
            return;
        }
        var status = $.trim( $(btn).data("status") );
        table.column(2).search(status).draw();
        if(status == ""){
            table.column(1).visible(true);
        }else{
            table.column(1).visible(false);
        }
    };
    window.registry.acl_type = function project_state(btn, table){
        if(!$(btn).hasClass("uk-active")){
            return;
        }
        var column_n = $.trim( $(btn).data("type") );

        if(column_n == ""){
            table.columns([8,10,12,14,16,18]).search("").draw();
            table.columns([7,9,11,13,15,17]).visible(true);
        }else{
            column_n = (column_n/1);
            table.columns([8,10,12,14,16,18]).search("");
            table.columns(column_n).search("True").draw();
            table.columns([7,9,11,13,15,17]).visible(false);
            table.columns([6]).visible(true);
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
    $(document).on("ready", function(){
        var table = $("#registry").DataTable({
            dom: "tip",
            pageLength: 100,
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
                data: "active",
                render: function ( date, type, row ) {
                    return row.active == "True" ? '<span class="btn uk-icon-check"></span>' : '';
                }
            },{
                data: "active",
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
                data: "user",
                render: function ( date, type, row ) {
                    return row.user == "True" ? '<span class="btn uk-icon-check"></span>' : '';
                }
            },{
                data: "user",
                visible: false
            },{
                data: "responsible",
                render: function ( date, type, row ) {
                    return row.responsible == "True" ? '<span class="btn uk-icon-check"></span>' : '';
                }
            },{
                data: "responsible",
                visible: false
            },{
                data: "manager",
                render: function ( date, type, row ) {
                    return row.manager == "True" ? '<span class="btn uk-icon-check"></span>' : '';
                }
            },{
                data: "manager",
                visible: false
            },{
                data: "tech",
                render: function ( date, type, row ) {
                    return row.tech == "True" ? '<span class="btn uk-icon-check"></span>' : '';
                }
            },{
                data: "tech",
                visible: false
            },{
                data: "committee",
                render: function ( date, type, row ) {
                    return row.committee == "True" ? '<span class="btn uk-icon-check"></span>' : '';
                }
            },{
                data: "committee",
                visible: false
            },{
                data: "admin",
                render: function ( date, type, row ) {
                    return row.admin == "True" ? '<span class="btn uk-icon-check"></span>' : '';
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
        $(document).on("click", ".edit_submit", submit);
        $(document).on("click", ".ed_mail", trigger_modal);
        $(document).on("click", ".user_activate", trigger_modal);
        $(document).on("click", ".user_add", trigger_modal);
        $(document).on("click", ".reset", trigger_modal);
        $(document).on("click", ".reset_submit", submit);
        $(document).on("change", ".project_select", function(){ window.registry.update_projects(this) });
        $(document).on("click", ".user-status", function(){ window.registry.user_status(this, table) });
        $(document).on("click", ".acl-type", function(){ window.registry.acl_type(this, table) });
        $(document).on("click", ".window_hide", trigger_modal);
        $(document).on("click", ".user_activate", function () {
            window.registry.update_projects(this)
        });
    });
})(window, document, jQuery);