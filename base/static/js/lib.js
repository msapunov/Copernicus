var contact = "mesocentre-techn@univ-amu.fr";
if(!String.prototype.f){
    // SOURCE: http://stackoverflow.com/questions/610406/javascript-equivalent-to-printf-string-format
    String.prototype.f = function(){
        var str = this.toString();
        if(!arguments.length)
            return str;
        var args = typeof arguments[0],
            args = (("string" === args || "number" === args) ? arguments : arguments[0]);
        for(var arg in args)
            str = str.replace(RegExp("\\{" + arg + "\\}", "gi"), args[arg]);
        return str;
    };
}

if(!String.prototype.capitalize){
    String.prototype.capitalize = function() {
        return this.charAt(0).toUpperCase() + this.slice(1);
    };
}
if(!String.prototype.idfy){
    String.prototype.idfy = function(){
        if(this.charAt(0) !== "#"){
            return "#" + this;
        }else{
            return this;
        }
    };
}
if(!String.prototype.hashCode){
    // SOURCE: http://stackoverflow.com/questions/7616461/generate-a-hash-from-string-in-javascript-jquery
    String.prototype.hashCode = function(){
        var hash = 0, i, chr, len;
        if (this.length === 0) return hash;
        for (i = 0, len = this.length; i < len; i++) {
            chr   = this.charCodeAt(i);
            hash  = ((hash << 5) - hash) + chr;
            hash |= 0; // Convert to 32bit integer
        }
        return "R"+hash;
    };
}
dialog=function(content, onconfirm, oncancel){
    var options = arguments.length > 1 && arguments[arguments.length-1] ? arguments[arguments.length-1] : {};
    onconfirm = UIkit.$.isFunction(onconfirm) ? onconfirm : function(){};
    oncancel  = UIkit.$.isFunction(oncancel) ? oncancel : function(){};
    options   = UIkit.$.extend(true, {bgclose:false, keyboard:false, modal:false, labels:UIkit.modal.labels}, UIkit.$.isFunction(options) ? {}:options);

    var modal = UIkit.modal.dialog(([
        '<div class="uk-margin uk-modal-content">'+String(content)+'</div>',
        '<div class="uk-modal-footer uk-text-right"><button class="uk-button js-modal-confirm-cancel">'+options.labels.Cancel+'</button> ',
        '<button class="uk-button uk-button-primary js-modal-confirm">'+options.labels.Ok+'</button></div>'
    ]).join(""), options);

    modal.element.find(".js-modal-confirm, .js-modal-confirm-cancel").on("click", function(){
        if(UIkit.$(this).is('.js-modal-confirm')){
            if(onconfirm()){
                modal.hide();
            }
        }else{
            (oncancel(), modal.hide());
        }
    });

    modal.on('show.uk.modal', function(){
        setTimeout(function(){
            modal.element.find('.js-modal-confirm').focus();
        }, 50);
    });
    modal.show();
    return modal;
};

show_error = function(req){
    var text = $.trim(req.responseText);
    var status = $.trim(req.status);
    var statText = $.trim(req.statusText);
    var msg;
    if((text) && (text.length > 0)){
        msg = "Status code: {0}\nMessage: {1}\n".f(status, text);
    }else{
        msg = "Server return {0}: {1}\n".f(status, statText);
    }
    msg += "Please contact technical team: {0}".f(contact);
    alert(msg);
};

modal = function(url, btn, fn){
    $.ajax({
        timeout: 60000,
        type: "POST",
        url: url,
        success: function(data){
            $("body").append(data);
            $("button."+btn).prop("disabled", false);
            if (typeof fn === "function") fn();
        }
    }).fail(function(request){
        show_error(request);
    });
};

form_reset = function(e){
    let form = $(e.target).find("form");
    $.each(form, function(key, value){
        value.reset();
    });
};

submit = function(e){
    var modal = $.trim( $(this).data("modal") );
    var form = $.trim( $(this).data("form") );
    var url = $.trim( $(this).data("url") );
    var data = $("#" + form).serialize();
    return ajax_send(url, data, modal);
};

ajax = function(url, data){
    UIkit.modal("#ajax_call", {modal: false}).show();
    return $.ajax({
        data: data ? data : undefined,
        timeout: 60000,
        type: "POST",
        url: url
    }).fail(function(reply){
        show_error(reply);
    }).always(function() {
        UIkit.modal("#ajax_call", {modal: false}).hide();
    });
};

ajax_send = function(url, data, show_modal){
    UIkit.modal("#ajax_call", {modal: false}).show();
    return $.ajax({
        data: data ? data : undefined,
        timeout: 60000,
        type: "POST",
        url: url
    }).done(function(reply){
        if (reply.message) {
            UIkit.notify(reply.message, {
                timeout: 3000,
                status: "success"
            });
        }
        if(show_modal){
            UIkit.modal("#" + show_modal).hide();
        }
    }).fail(function(reply){
        show_error(reply);
    }).always(function() {
        UIkit.modal("#ajax_call", {modal: false}).hide();
    });

};

json_send = function(url, data, show_modal){
    var modal = {show: function(){}, hide: function(){}};
    if(typeof(show_modal)==='undefined'){
        modal = UIkit.modal("#ajax_call", {modal: false});
    }
    modal.show();
    return $.ajax({
        contentType: "application/json",
        data: data ? JSON.stringify(data) : undefined,
        dataType: "json",
        timeout: 60000,
        type: "POST",
        url: url
    }).fail(function(request){
        show_error(request);
    }).always(function() {
        modal.hide();
    });
};

trigger_modal = function(e){
    var name = $.trim( $(this).data("modal") );
    var modal = UIkit.modal("#" + name);
    if ( modal.isActive() ) {
        modal.hide();
    } else {
        modal.show();
    }
};
/*
trigger_modal = function(modal){
    if( modal.isActive() ){
        modal.hide();
    }else{
        modal.show();
    }
};
*/
data_check = function(data){
    var result = true;
    $.each(data, function(key, value){
        if(value.length < 1){
            $("[name={0}]".f(key)).addClass("uk-form-danger");
            result = false;
        }
    });
    return result
};