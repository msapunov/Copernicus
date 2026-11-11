(function(window, document, $, undefined){
    "use strict";
    let url = "user/modal/edit";
    let ssh = "user/modal/ssh";
    let del = "user/modal/ssh/delete";
    let pass = "reset.html"

    window.render = function(html){
        const $modal = $("<div>").html(html).find(".uk-modal").first();
        if (!$modal.length) return;

        const modalId = $modal.attr("id");
        if (!modalId) return

        if (!$("#" + modalId).length) {
            $("body").append($modal);
        }
        const modal = UIkit.modal("#" + modalId);
        modal.isActive() ? modal.hide() : modal.show();
    };

    window.key_submit = function (e) {
        let req = submit.call(this, e);
        req.done(function(response) {
            $("#public_key").replaceWith(response.html);
        });
    }

    window.key_delete = function(e){
        let kid = $(this).data("key-id");
        let login = $(this).data("login");
        let url = del + "/" + login + "/" + kid;
        new_modal(url, $(this), window.render);
    };

    $(document).on("ready", function(){
        let login = $.trim( $("#user_login").data("login") );
        modal("{0}/{1}".f(url, login), "edit");
        modal(ssh, "ssh");
    });

    function reset() {
        window.location.href = pass;
    }

    $(document).on("click", ".window_hide", trigger_modal);
    $(document).on("click", ".edit", trigger_modal);
    $(document).on("click", ".ssh", trigger_modal);
    $(document).on("click", ".key_rename", trigger_modal);
    $(document).on("click", ".key_delete", window.key_delete);
    $(document).on("click", ".pass", reset);
    $(document).on("click", ".edit_submit", submit);
    $(document).on("click", ".ssh_submit", submit);
    $(document).on("click", ".key_rename_submit", submit);
    $(document).on("click", ".key_delete_submit", submit);
    $(document).on("hide.uk.modal", form_reset);

})(window, document, jQuery);