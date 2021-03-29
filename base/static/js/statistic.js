(function(window, document, $, undefined){
    "use strict";
    window.stat = {};
    window.stat.url = {
        list: "statistic/list",
        suspend: "statistic/suspend/",
        activate: "statistic/activate/"
    };
    window.stat.users = function users(users){
        if(users.length < 1){
            return "-";
        }
        var ul = $("<ul/>").attr({"style":"list-style: none;"});
        $.each(users, function(idx, v){
            var li = $("<li/>");
            var user = v.fullname + " <" + v.email + "> [" + v.login +"] ";
            li.text(user);
            ul.append(li);
        });
        return ul.prop("outerHTML")
    };
    window.stat.project_type = function project_type(btn, table){
        if(!$(btn).hasClass("uk-active")){
            return;
        }
        var type = $.trim( $(btn).data("type") );
        table.columns(1).search(type).draw();
    };
    window.stat.change_responsible = function change_responsible(btn, dt){
        var name = $.trim( $(btn).data("name") );
        var pid = $.trim( $(btn).data("pid") );
        var rid = $.trim( $(btn).data("row") );
        var text = "Please select new responsible for the project '";
        text += name + "' from the list";
        UIkit.modal.confirm(text, function(){
            json_send(url).done(function(reply){
                var row = dt.row(rid);
                row.data(reply.data).draw();
                row.child.hide();
                row.child(window.stat.expand(row.data(), row)).show();
                var tdi = $(row.node()).find("span.btn");
                tdi.first().removeClass("uk-icon-plus");
                tdi.first().addClass("uk-icon-minus");
            })
        });
    };
    window.stat.set_state = function set_state(state, dt, btn){
        // activate - true
        // suspend - false
        var name = $.trim( $(btn).data("name") );
        var id = $.trim( $(btn).data("pid") );
        var rid = $.trim( $(btn).data("row") );
        if(state){
            var text = "Activate project " + name + "? ";
            var url = window.stat.url.activate + id;
        }else{
            var text = "Suspend project " + name + "? ";
            var url = window.stat.url.suspend + id;
        }
        text = text + "That change affects database only.";
        UIkit.modal.confirm(text, function(){
            json_send(url).done(function(reply){
                var row = dt.row(rid);
                row.data(reply.data).draw();
                row.child.hide();
                row.child(window.stat.expand(row.data(), row)).show();
                var tdi = $(row.node()).find("span.btn");
                tdi.first().removeClass("uk-icon-plus");
                tdi.first().addClass("uk-icon-minus");
            })
        });
    };
    window.stat.project_state = function project_state(btn, table){
        if(!$(btn).hasClass("uk-active")){
            return;
        }
        var state = $.trim( $(btn).data("state") );
        table.columns(11).search(state).draw();
    };
    window.stat.percentage = function percentage(percent, total) {
        if( percent == 0 && total == 0){
            return "0";
        }
        return ((percent * 100) / total).toFixed(2);
    };
    window.stat.btnAddUser = function btnAddUser(pid, name, rid){
        return '<button class="uk-button add-user uk-width-1-1 uk-margin-small-bottom" data-pid=' +
            pid +
            ' data-name=' +
            name +
            ' data-row=' +
            rid +
            ' type="button">Add user</button>';
    };
    window.stat.btnState = function btnState(pid, name, state, rid){
        if(state){
            return '<button class="uk-button suspend uk-width-1-1 uk-margin-small-bottom" data-pid=' +
            pid +
            ' data-name=' +
            name +
            ' data-row=' +
            rid +
            ' type="button">Suspend project</button>';
        }else{
            return '<button class="uk-button activate uk-width-1-1 uk-margin-small-bottom" data-pid=' +
            pid +
            ' data-name=' +
            name +
            ' data-row=' +
            rid +
            ' type="button">Activate project</button>';
        }
    };
    window.stat.btnChangeResp = function btnChangeResp(pid, name, rid){
        return '<button class="uk-button change-responsible uk-width-1-1 uk-margin-small-bottom" data-pid=' +
        pid +
        ' data-name=' +
        name +
        ' data-row=' +
        rid +
        ' type="button">Change responsible</button>';
    };
    window.stat.expand = function format(d, row){
        // `d` is the original data object for the row
        var stat = (d.active) ? 'Active' : 'Suspended';
        var resp = (d.responsible) ? d.responsible.fullname + ' &lt;' + d.responsible.email + '&gt;' + ' [' + d.responsible.login + ']' : "-";
        var proc = (d.consumed_use > 0) ? d.consumed_use+"%" : "-" ;
        var rid = row.index();
        var btnState = window.stat.btnState(d.id, d.name, d.active, rid);
        var btnChangeResp = window.stat.btnChangeResp(d.id, d.name, rid);
        var btnAddUser = window.stat.btnAddUser(d.id, d.name, rid);
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
                '<div>Users: ' + window.stat.users(d.users) + '</div>' +
                '<div>Genci: ' + d.genci_committee + '</div>' +
                '<div>Scientific fields: ' + d.scientific_fields + '</div>' +
            '</div>' +
            '<div class="uk-width-1-4">' +
                '<div>' +
                    btnState +
                '</div>' +
                /*
                '<div>' +
                    btnChangeResp +
                '</div>' +
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

        var table = $("#statistics").DataTable({
            ajax: {type: "POST", url: window.stat.url.list},
            dom: 't',
            footerCallback: function( tfoot, data, start, end, display ) {
                var api = this.api();
                var conso = api.column( 5, { page: 'current'} ).data().reduce( function ( a, b ) {
                    return a + b;
                }, 0 )
                var total = api.column( 6, { page: 'current'} ).data().reduce( function ( a, b ) {
                    return a + b;
                }, 0 )
                var dp = window.stat.percentage(conso, total) + "%";
                var dc = new Intl.NumberFormat().format(conso);
                var dt = new Intl.NumberFormat().format(total);
                var all = "Consumed: " + dc + " Total: " + dt + " (" + dp + ")";
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
                data: "allocation_start",
                render: function ( data, type, row ) {
                    var dateSplit = data.split(' ');
                    return type === "display" || type === "filter" ? dateSplit[0] : data;
                }
            },{
                data: "allocation_end",
                render: function ( data, type, row ) {
                    var dateSplit = data.split(' ');
                    return type === "display" || type === "filter" ? dateSplit[0] : data;
                }
            },{
                data: "responsible.fullname",
                render: function ( data, type, row ) {
                    if(! data){
                        return "-";
                    }else{
                        return data;
                    }
                }
            },{
                data: "consumed",
                render: function ( data, type, row ) {
                    if(! data){
                        return "-";
                    }else{
                        return new Intl.NumberFormat().format(data);
                    }
                }
            },{
                data: "resources.cpu",
                render: $.fn.dataTable.render.number( '.', '')
            },{
                data: "consumed_use",
                render: function ( data, type, row ) {
                    if(data > 0){
                        return data+"%";
                    }else{
                        return "-";
                    }
                }
            },{
                data: "genci_committee",
                visible: false
            },{
                data: "users",
                render: function ( data, type, row ) {
                    var users = "";
                    $.each(data, function(idx, v){
                        var user = v.fullname + " <" + v.email + "> [" + v.login +"] ";
                        users += user;
                    });
                    return users
                },
                visible: false
            },{
                data: "title",
                visible: false
            },{
                data: "active",
                visible: false
            },{
                data: "scientific_fields",
                visible: false
            }],
            order: [[1, 'asc']]
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
                row.child(window.stat.expand(row.data(), row)).show();
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

        $(document).on("click", ".project-state", function(){ window.stat.project_state(this, table)});
        $(document).on("click", ".project-type", function(){ window.stat.project_type(this, table)});
        $(document).on("click", ".suspend", function(){ window.stat.set_state(false, table, this)});
        $(document).on("click", ".activate", function(){ window.stat.set_state(true, table, this)});
        $(document).on("click", ".change-responsible", function(){ window.stat.change_responsible(this, table)});
    });

})(window, document, jQuery);