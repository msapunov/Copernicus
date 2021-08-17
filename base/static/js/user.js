(function(window, document, $, undefined){
    "use strict";
    window.user = {};
    window.user.url = {
        modal: "user/modal/edit",
        edit: "user/edit"
    };

    window.user.edit=function(e){
        var modal = $.trim( $(this).data("modal") );
        var form = $.trim( $(this).data("form") );
        var data = $("#" + form).serialize()
        ajax_send(window.user.url.edit, data, modal);
        e.preventDefault();
    }

    $(document).on("ready", function(){
        var login = $.trim( $("#user_login").data("login") );
        modal("{0}/{1}".f(window.user.url.modal, login), "edit");
    });

    $(document).on("click", ".window_hide", trigger_modal);
    $(document).on("click", ".edit", trigger_modal);
    $(document).on("click", ".edit_submit", window.user.edit);
    $(document).on({
        mouseenter: function () {
            $(".user_info_edit").toggleClass("uk-hidden");
        },
        mouseleave: function () {
            $(".user_info_edit").toggleClass("uk-hidden");
        }
    }, ".user_info");

})(window, document, jQuery);