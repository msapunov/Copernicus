(function(window, document, $, undefined){
    "use strict";
    let url = "user/modal/edit";
    let ssh = "user/modal/ssh";

    $(document).on("ready", function(){
        var login = $.trim( $("#user_login").data("login") );
        modal("{0}/{1}".f(url, login), "edit");
        modal(ssh, "ssh");
    });

    $(document).on("click", ".window_hide", trigger_modal);
    $(document).on("click", ".edit", trigger_modal);
    $(document).on("click", ".ssh", trigger_modal);
    $(document).on("click", ".edit_submit", submit);
    $(document).on("click", ".ssh_submit", submit);
    $(document).on("hide.uk.modal", form_reset);

})(window, document, jQuery);