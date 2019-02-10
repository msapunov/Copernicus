if(!String.prototype.f){
    // SOURCE: http://stackoverflow.com/questions/610406/javascript-equivalent-to-printf-string-format
    String.prototype.f = function(){
        var str = this.toString();
        if(!arguments.length)
            return str;
        var args = typeof arguments[0],
            args = (("string" == args || "number" == args) ? arguments : arguments[0]);
        for(arg in args)
            str = str.replace(RegExp("\\{" + arg + "\\}", "gi"), args[arg]);
        return str;
    }
}

if(!String.prototype.capitalize){
    String.prototype.capitalize = function() {
        return this.charAt(0).toUpperCase() + this.slice(1);
    }
}
if(!String.prototype.idfy){
    String.prototype.idfy = function(){
        if(this.charAt(0) != "#"){
            return "#" + this;
        }else{
            return this;
        }
    }
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
    return modal.show();
};

show_error = function(req){
    var text = $.trim(req.responseText);
    var status = $.trim(req.status);
    var statText = $.trim(req.statusText);
    if((text) && (text.length > 0)){
        var msg = "Status code: {0}\nMessage: {1}\n".f(status, text);
    }else{
        var msg = "Server return {0}: {1}\n".f(status, statText);
    }
    msg += "Please contact technical team: {0}".f(window.contact);
    alert(msg);
};

json_send = function(url, data){
    var modal = UIkit.modal.blockUI("Sending data...");
    return $.ajax({
        contentType: "application/json",
        data: JSON.stringify(data),
        dataType: "json",
        timeout: 5000,
        type: "POST",
        url: url
    }).done(function(resp){
        UIkit.notify("Data exchange finished successfully", {timeout: 2000, status:"success"});
    }).fail(function(request){
        show_error(request);
    }).always(function() {
        modal.hide();
    });
}