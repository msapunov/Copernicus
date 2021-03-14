(function(window, document, $, undefined){
    "use strict";
    window.stat = {};
    window.stat.url = {
        list: "statistic/list",
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
    }
    window.stat.expand = function format(d){
        // `d` is the original data object for the row
        var stat = (d.active) ? 'Active' : 'Postponed';
        var resp = (d.responsible) ? d.responsible.fullname + ' &lt;' + d.responsible.email + '&gt;' + ' [' + d.responsible.login + ']' : "-";
        var proc = (d.consumed_use > 0) ? d.consumed_use+"%" : "-" ;
        return '<div class="uk-panel uk-margin-top uk-margin-bottom" style="padding-left:50px;padding-right:50px;">' +
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
            '<div class="uk-panel" style="padding-left:50px;padding-right:50px;">' +
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
            '</div>';
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
                render: $.fn.dataTable.render.number( ',', '')
            },{
                data: "resources.cpu",
                render: $.fn.dataTable.render.number( ',', '')
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
                row.child(window.stat.expand(row.data())).show();
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
    });

})(window, document, jQuery);