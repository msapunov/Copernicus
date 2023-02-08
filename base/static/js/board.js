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
    window.board.update = function update(dt, rid, data){
        var row = dt.row(rid);
        row.data(data).draw();
        row.child.hide();
        row.child(window.board.expand(row.data(), row)).show();
        var tdi = $(row.node()).find("span.btn");
        tdi.first().removeClass("uk-icon-plus");
        tdi.first().addClass("uk-icon-minus");
    };
    window.board.project_type = function project_type(btn, table){
        if(!$(btn).hasClass("uk-active")){
            return;
        }
        var type = $.trim( $(btn).data("type") );
        if (type == "extension"){
            var tt = table.column(6).data();
            table.column(6).search().draw();
        }else if(type == "renewal"){
            table.columns(7).search(Boolean(), true).draw();
        }else if(type == "activate"){
            table.columns(8).search().draw();
        }else if(type == "transform"){
            table.columns(9).search("").draw();
        }else {
            table.columns().search("").draw();
        }
    };
    window.board.resp_submit = function resp_submit(btn, dt){
        var pid = $(".change-responsible").data("pid");
        var rid = $(".change-responsible").data("row");
        var uid = $("#form_responsible").serialize().replace("change_responsible=", "");
        var url = window.board.url.set_responsible + pid;
        json_send(url, {"uid": uid}).done(function(reply){
            if(reply.data){
                UIkit.notify(reply.data, {timeout: 2000, status:"success"});
                window.board.update(dt, rid, reply.data);
            }
        });
    };
    window.board.change_responsible = function change_responsible(btn, dt){
        var name = $.trim( $(btn).data("name") );
        var pid = $.trim( $(btn).data("pid") );
        var rid = $.trim( $(btn).data("row") );
        var resp = $.trim( $(btn).data("responsible") );
        $(".change_resp_project_placeholder").text(name);
        $(".change_resp_current_placeholder").text(resp);
        var modal = UIkit.modal("#change_responsible");
        if ( modal.isActive() ) {
            modal.hide();
        } else {
            modal.show();
        }
    };
    window.board.dump = function dump(type, e){
        if(!type in ["csv", "ods", "xls"]){
            e.preventDefault();
            alert("Extension " + type + " is not supported");
            return;
        }
        var data = $("#statistics").DataTable().rows({search:'applied'}).data().toArray();
        if(data.length < 1){
            e.preventDefault();
            alert("No records to save, table is empty!");
            return;
        }
        var pid=[];
        data.forEach(function(row) {
            pid.push(row.name);
        });

        var url = "projects." + type + "?projects=" + pid.join(",");
        var id = ".dump_" + type;
        var anchor = $(id);
        anchor.attr("href", url);
    };
    window.board.percentage = function percentage(percent, total) {
        if( percent == 0 && total == 0){
            return "0";
        }
        return ((percent * 100) / total).toFixed(2);
    };
    window.board.expand = function format(d, row){
        // `d` is the original data object for the row
        var stat = (d.active) ? 'Active' : 'Suspended';
        var resp = (d.responsible) ? d.responsible.fullname + ' &lt;' + d.responsible.email + '&gt;' + ' [' + d.responsible.login + ']' : "-";
        var lab = (d.responsible) ? d.responsible.lab : "-";
        var phone = (d.responsible) ? d.responsible.phone : "-";
        var proc = (d.consumed_use > 0) ? d.consumed_use+"%" : "-" ;
        var rid = row.index();
        var btnState = window.board.btnState(d.id, d.name, d.active, rid);
        var btnConso = window.board.btnConso(d.id, d.name, rid);
        var btnAddUser = window.board.btnAddUser(d.id, d.name, rid);
        return '<div class="uk-grid"><div class="uk-width-3-4 uk-panel uk-margin-top uk-margin-bottom" style="padding-left:50px;padding-right:50px;">' +
                '<div>ID: <b>' + d.id + '</b></div>' +
                '<div>Name: <b>' + d.name + '</b></div>' +
                '<div>Title: ' + d.title + '</div>' +
                '<div>Status: <b>' + stat + '</b></div>' +
                '<div>Created: ' + d.created + '</div>' +
                '<div>CPU allocation kickoff: ' + d.allocation_start + '</div>' +
                '<div>CPU allocation deadline: ' + d.allocation_end + '</div>' +
                '<div>Consumption: ' + d.consumed + '</div>' +
                '<div>Total: ' + d.resources.cpu + '</div>' +
                '<div>Usage: ' + proc + '</div>' +
                '<div>Responsible: ' + resp + '</div>' +
                '<div>Lab: ' + lab + '</div>' +
                '<div>Phone: ' + phone + '</div>' +
                '<div>Users: ' + window.board.users(d.users) + '</div>' +
                '<div>Genci: ' + d.genci_committee + '</div>' +
                '<div>Scientific fields: ' + d.scientific_fields + '</div>' +
            '</div>' +
            '<div class="uk-width-1-4">' +
                '<div>' +
                    btnState +
                '</div>' +
                '<div>' +
                    btnConso +
                '</div>' +
                /*
                '<div>' +
                    btnAddUser +
                '</div>' +
                */
            '</div>' +
            '<div class="uk-width-1-1 uk-panel" style="padding-left:50px;padding-right:50px;">' +
                '<ul class="uk-subnav uk-subnav-pill" data-uk-switcher="{connect:\'#' + d.name + '-additional-info\'}">' +
                    '<li class="uk-active"><a href="">Description</a></li>' +
                    '<li><a href="">Methods</a></li>' +
                    '<li><a href="">Resources</a></li>' +
                    '<li><a href="">Management</a></li>' +
                    '<li><a href="">Motivation</a></li>' +
                '</ul>' +
                '<ul id="' + d.name + '-additional-info" class="uk-switcher">' +
                    '<li><article class="ws">' + d.description + '</article></li>' +
                    '<li><article class="ws">' + d.numerical_methods + '</article></li>' +
                    '<li><article class="ws">' + d.computing_resources + '</article></li>' +
                    '<li><article class="ws">' + d.project_management + '</article></li>' +
                    '<li><article class="ws">' + d.project_motivation + '</article></li>' +
                '</ul>' +
            '</div></div>';
    };

    $(document).ready(function(){
        var table = $("#board").DataTable({
            ajax: {type: "POST", url: window.board.url.list},
            dom: 't',
            footerCallback: function( tfoot, data, start, end, display ) {
                var api = this.api();
                var total = api.column( 3, { page: 'current'} ).data().reduce( function ( a, b ) {
                    return a + b;
                }, 0 )
                var req = api.column( 11, { page: 'current'} ).data().reduce( function ( a, b ) {
                    return a + b;
                }, 0 )
                var dc = new Intl.NumberFormat().format(total);
                var dt = new Intl.NumberFormat().format(req);
                var all = "Present: " + dc + " Requested: " + dt ;
                $("#table_total").text(all);
            },
            drawCallback: function( settings ) {
                var api = this.api();
                var info = api.page.info();
                var total = info.recordsTotal;
                var shown = info.recordsDisplay;
                var start = info.start + 1;
                var end = info.end;
                if(total === 0){
                    var txt = "Showing " + total + " entries";
                }else if(total != shown){
                    var txt = "Showing " + start + " to " + end + " of " + shown + " entries (filtered from " + total + " total entries)";
                }else{
                    var txt = "Showing " + start + " to " + shown + " of " + total + " entries";
                }
                $("#table_info").text(txt);
            },
            initComplete: function(settings, json) {
                $()
            },
            paging: false,
            searching: true,
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
                data: "name"
            },{
                data: "responsible"
            },{
                data: "total",
                render: $.fn.dataTable.render.number( ',', '')
            },{
                data: "present_use",
                render: $.fn.dataTable.render.number( ',', '')
            },{
                data: "present_usage",
                render: function ( data, type, row ) {
                    return data+"%";
                }
            },{
                data: "extension",
                render: function ( data, type, row ) {
                    if(data == true){
                        //return row.hours.fn.dataTable.render.number( ',', '')
                        return new Intl.NumberFormat().format(row.hours);
                    }
                }
            },{
                data: "extension",
                render: function ( data, type, row ) {
                    if(data != true){
                        return new Intl.NumberFormat().format(row.hours);
                    }
                }
            },{
                data: "activate",
                defaultContent: '',
                render: function ( data, type, row ) {
                    if(data == true) {
                        return '<span class="btn uk-icon-check"></span>';
                    }
                },
                width:"15px"
            },{
                data: "transform",
                defaultContent: '',
                render: function ( data, type, row ) {
                    if(data != " ") {
                        return '<span class="btn uk-icon-refresh uk-margin-small-right"></span>' + data.toUpperCase();
                    }
                },
                width:"15px"
            },{
                data: "created",
                render: function ( data, type, row ) {
                    var dateSplit = data.split(' ');
                    return type === "display" || type === "filter" ? dateSplit[0] : data;
                }
            },{
                data: "hours",
                visible: false
            }],
            order: [[10, 'desc']]
        });

        $('#statistics tbody').on('click', 'td.details-control', function () {
            var tr = $(this).closest('tr');
            var tdi = tr.find("span.btn");
            var row = table.row(tr);
            if (row.child.isShown()) {
                // This row is already open - close it
                row.child.hide();
                tr.removeClass('shown');
                tdi.first().removeClass('uk-icon-minus');
                tdi.first().addClass('uk-icon-plus');
            }else {
                // Open this row
                row.child(window.board.expand(row.data(), row)).show();
                tr.addClass('shown');
                tdi.first().removeClass('uk-icon-plus');
                tdi.first().addClass('uk-icon-minus');
            }
        });

        table.on("user-select", function (e, dt, type, cell, originalEvent) {
            if ($(cell.node()).hasClass("details-control")) {
                e.preventDefault();
            }
        });
        $("#table_search").on( "keyup", function () {
            table.search( this.value ).draw();
        } );

        $(document).on("click", ".ext-type", function(){ window.board.project_type(this, table) });
        $(document).on("click", ".dump_csv", function(e){window.board.dump("csv", e) });
        $(document).on("click", ".dump_ods", function(e){ window.board.dump("ods", e) });
        $(document).on("click", ".dump_xls", function(e){ window.board.dump("xls", e) });
        $(document).on("click", ".suspend", function(){ window.board.set_state(false, table, this) });
        $(document).on("click", ".activate", function(){ window.board.set_state(true, table, this) });
        $(document).on("click", ".actualize", function(){ window.board.actualize(true, table, this) });
        $(document).on("click", ".change-responsible", function(){ window.board.change_responsible(this, table) });
    });

})(window, document, jQuery);
