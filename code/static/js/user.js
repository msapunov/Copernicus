(function(window, document, $, undefined){
    "use strict";
    window.user = {};
    window.user.url = "user/edit/info";

    window.user.edit=function(){
        var login = $.trim( $(this).data("login") );
        var name = $.trim( $(this).data("name") );
        var surname = $.trim( $(this).data("surname") );
        var email = $.trim( $(this).data("email") );

        var title = "Change person information for account '{0}'?".f(login);
        var n_field = $("<input/>").addClass("uk-width-1-1").attr({
            "name": "name",
            "type": "text",
            "value": name.capitalize()
        });
        var s_field = $("<input/>").addClass("uk-width-1-1").attr({
            "name": "surname",
            "type": "text",
            "value": surname.capitalize()
        });
        var e_field = $("<input/>").addClass("uk-width-1-1").attr({
            "name": "email",
            "type": "email",
            "value": email
        });
        var form = $("<form/>").addClass("uk-form").append(
            $("<legend/>").text(title)
        ).append(
          $("<div/>").addClass("uk-form-row").append(n_field)
        ).append(
          $("<div/>").addClass("uk-form-row").append(s_field)
        ).append(
          $("<div/>").addClass("uk-form-row").append(e_field)
        ).append(
          $("<div/>").text("Please double check if provided data are correct").attr({"id":"psa"}).addClass("uk-form-row uk-alert")
        );
        var popup = dialog(form.prop("outerHTML"), function(){
            var data = {
                "name": $("input[name=name]").val(),
                "surname": $("input[name=surname]").val(),
                "email": $("input[name=email]").val(),
                "login": login
            };
            if( ! data_check(data) ){

                return false;
            }
            //window.proj.send("add", data);
            popup.hide();
        });
    }

    $(document).on("click", ".edit", window.user.edit);

})(window, document, jQuery);