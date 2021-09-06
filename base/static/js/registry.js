(function(window, document, $, undefined){
    "use strict";
    window.registry = {};
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
    $(document).on("ready", function(){
        var table = $("#registry").DataTable({
            dom: "tip",
            pageLength: 100,
            columns: [{
                className: 'details-control',
                orderable: false,
                data: null,
                defaultContent: '',
                //render: function () {
                //    return '<span class="btn uk-icon-plus"></span>';
                //},
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
        $("#table_search").on( "keyup", function () {
            table.search( this.value ).draw();
        });
        $(document).on("click", ".user_add", trigger_modal);
        $(document).on("click", ".user-status", function(){ window.registry.user_status(this, table) });
        $(document).on("click", ".acl-type", function(){ window.registry.acl_type(this, table) });
        $(document).on("click", ".window_hide", trigger_modal);
    });
})(window, document, jQuery);