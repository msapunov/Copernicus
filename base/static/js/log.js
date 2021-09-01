(function(window, document, $, undefined){
    "use strict";

    $(document).on("ready", function(){
        $("#events").DataTable({
            dom: "ftip",
            lengthMenu: [ 100, 250, 500, 1000 ],
            pageLength: 100,
            columns: [{
                data: "item"
            },{
                data: "message"
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
            }]
        });
    });
})(window, document, jQuery);