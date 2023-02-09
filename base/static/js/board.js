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
        expand: "board/expand",
        global_history: "board/history"
    };
    window.board.project_type = function project_type(btn, table){
        if(!$(btn).hasClass("uk-active")){
            return;
        }
        table.columns().search("").draw();
        var type = $.trim( $(btn).data("type") );
        if (type == "extension"){
            var tt = table.column(6).data();
            table.columns(6).search("\\d+", true).draw();
        }else if(type == "renewal"){
            table.columns(7).search("\\d+", true).draw();
        }else if(type == "activate"){
            table.columns(8).search("\\d+").draw();
        }else if(type == "transform"){
            table.columns(9).search("\\w+", true).draw();
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

    window.board.expand_processing = function(tr, tdi, show){
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
    window.board.expand = function format(d, row, tr, tdi){
        // `d` is the original data object for the row
        let id = d.id;
        let url = "{0}/{1}".f(window.board.url.expand, id);
        window.board.expand_processing(tr, tdi);
        ajax(url).done(function(data){
            row.child(data).show();
            window.board.expand_processing(tr, tdi, false);
        }).fail(function(request){
            window.board.expand_processing(tr, tdi, true);
        });
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
                defaultContent: 0,
                render: $.fn.dataTable.render.number( ',', '')
            },{
                data: "present_usage",
                render: function ( data, type, row ) {
                    return data+"%";
                }
            },{
                data: "extension",
                defaultContent: "",
                render: function ( data, type, row ) {
                    if(data == true){
                        //return row.hours.fn.dataTable.render.number( ',', '')
                        return new Intl.NumberFormat().format(row.hours);
                    }
                }
            },{
                data: null,
                defaultContent: "",
                render: function ( data, type, row ) {
                    if(row.extension != true){
                        return new Intl.NumberFormat().format(row.hours);
                    }
                }
            },{
                data: "activate",
                defaultContent: "",
                render: function ( data, type, row ) {
                    if(data == true) {
                        return '<span class="btn uk-icon-check"></span>';
                    }
                },
                width:"15px"
            },{
                data: "transform",
                defaultContent: "",
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
            }]
        });
        $('#board tbody').on('click', 'td.details-control', function () {
            let tr = $(this).closest('tr');
            let tdi = tr.find("span.btn");
            let row = table.row(tr);
            if (row.child.isShown()) {
                // This row is already open - close it
                row.child.hide();
                window.board.expand_processing(tr, tdi, true);
            }else {
                // Open row in ajax callback in function window.board.expand
                window.board.expand(row.data(), row, tr, tdi);
            }
        });

        $("#table_search").on( "keyup", function () {
            table.search( this.value ).draw();
        } );

        $(document).on("click", ".ext-type", function(){ window.board.project_type(this, table) });
        $(document).on("click", ".dump_csv", function(e){window.board.dump("csv", e) });
        $(document).on("click", ".dump_ods", function(e){ window.board.dump("ods", e) });
        $(document).on("click", ".dump_xls", function(e){ window.board.dump("xls", e) });
        $(document).on("click", ".history", trigger_modal);
        $(document).on("click", ".contact", trigger_modal);
        $(document).on("click", ".accept", trigger_modal);
        $(document).on("click", ".ignore", trigger_modal);
        $(document).on("click", ".reject", trigger_modal);
        $(document).on("click", ".accept_submit", submit);
        $(document).on("click", ".ignore_submit", submit);
        $(document).on("click", ".reject_submit", submit);

        $(document).on("click", ".window_hide", trigger_modal);
    });

})(window, document, jQuery);
