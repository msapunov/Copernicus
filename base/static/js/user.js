(function(window, document, $, undefined){
    "use strict";
    let url = "user/modal/edit";

    $(document).on("ready", function(){
        var login = $.trim( $("#user_login").data("login") );
        modal("{0}/{1}".f(url, login), "edit");
    });

    $(document).on("click", ".window_hide", trigger_modal);
    $(document).on("click", ".edit", trigger_modal);
    $(document).on("click", ".edit_submit", submit);
    $(document).on({
        mouseenter: function () {
            $(".edit").toggleClass("uk-hidden");
        },
        mouseleave: function () {
            $(".edit").toggleClass("uk-hidden");
        }
    }, ".user_info");
    $(document).on("hide.uk.modal", form_reset);

})(window, document, jQuery);