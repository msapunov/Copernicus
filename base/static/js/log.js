(function(window, document, $, undefined){
    "use strict";
    window.log = {};
    window.log.items = function project_state(btn, table){
        if(!$(btn).hasClass("uk-active")){
            return;
        }
        let items = $.trim( $(btn).data("items") );
        table.page.len( items ).draw();
    };
    $(document).on("ready", function(){
        var table = $("#events").DataTable({
            dom: "tip",
            pageLength: 100,
            columns: [{
                data: "item",
                visible: false
            },{
                data: "message",
                render: function ( data, type, row ) {
                    let cat = row.category;
                    if(cat=="project" || cat == "registration"){
                        return "<b>" + row.item + ":</b>&nbsp;" + data;
                    }else{
                        return data;
                    }
                }
            },{
                data: "date",
                render: function ( date, type, row ) {
                    let dateSplit = date.split(' ');
                    let full = row.date_full
                    return type === "display" || type === "filter" ? '<div title="' + full + '">' + dateSplit[0] : date;
                }
            },{
                data: "date_full",
                visible: false
            },{
                data: "category",
                visible: false
            }]
        });
        $("#table_search").on( "keyup", function () {
            table.search( this.value ).draw();
        });
        $(document).on("click", ".items", function(){ window.log.items(this, table) });
    });
})(window, document, jQuery);