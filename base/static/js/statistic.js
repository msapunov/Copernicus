(function(window, document, $, undefined){
    "use strict";
    window.stat = {};
    window.stat.url = {
        list: "statistic/list",
        history: "project/history",
        expand: "statistic/expand"
    };
    window.stat.percentage = function percentage(percent, total) {
        if( percent == 0 && total == 0){
            return "0";
        }
        return ((percent * 100) / total).toFixed(2);
    };
    window.stat.project_type = function project_type(btn, table){
        if(!$(btn).hasClass("uk-active")){
            return;
        }
        $(".conso").removeClass("uk-active");
        $(".conso_all").addClass("uk-active");
        let extype = $.trim( $(btn).data("type") );
        table.columns(13).search(extype).draw();
    };
    window.stat.submit = function (e) {
        let x = submit.call(this);
        x.done(function (reply) {
            UIkit.modal("#ajax_call", {modal: false}).hide();
            let id = reply.data.id;
            $("table#board").DataTable().row("#" + id).remove().draw();
        });
    }
    window.stat.dump = function dump(type, e){
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

    window.stat.expand_processing = function(tr, tdi, show){
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
    window.stat.expand = function format(d, row, tr, tdi){
        // `d` is the original data object for the row
        let id = d.name;
        let url = "{0}/{1}".f(window.stat.url.expand, id);
        window.stat.expand_processing(tr, tdi);
        ajax(url).done(function(data){
            row.child("<div class='uk-grid'>" + data + "</div>").show();
            window.stat.expand_processing(tr, tdi, false);
        }).fail(function(request){
            window.stat.expand_processing(tr, tdi, true);
        });
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
                        var user = v.fullname + " " + v.email + " " + v.login + " ";
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
                data: "responsible.lab",
                visible: false
            },{
                data: "scientific_fields",
                visible: false
            },{
                data: "description",
                visible: false
            },{
                data: "ref",
                visible: false
            },{
                data: "numerical_methods",
                visible: false
            }]
        });
        $('#statistics tbody').on('click', 'td.details-control', function () {
            let tr = $(this).closest('tr');
            let tdi = tr.find("span.btn");
            let row = table.row(tr);
            if (row.child.isShown()) {
                // This row is already open - close it
                row.child.hide();
                window.stat.expand_processing(tr, tdi, true);
            }else {
                // Open row in ajax callback in function window.board.expand
                window.stat.expand(row.data(), row, tr, tdi);
            }
        });

        $("#table_search").on( "keyup", function () {
            table.search( this.value ).draw();
        } );

        $(document).on("click", ".project-state", function(){ window.stat.project_state(this, table) });
        $(document).on("click", ".project-type", function(){ window.stat.project_type(this, table) });
        $(document).on("click", ".dump_csv", function(e){window.stat.dump("csv", e) });
        $(document).on("click", ".dump_ods", function(e){ window.stat.dump("ods", e) });
        $(document).on("click", ".dump_xls", function(e){ window.stat.dump("xls", e) });
        $(document).on("click", ".suspend", function(){ window.stat.set_state(false, table, this) });
        $(document).on("click", ".activate", function(){ window.stat.set_state(true, table, this) });
        $(document).on("click", ".history", trigger_modal);
        $(document).on("click", ".contact", trigger_modal);
        $(document).on("click", ".message_submit", submit);

        $(document).on("click", ".window_hide", trigger_modal);
    });

})(window, document, jQuery);
