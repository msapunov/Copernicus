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

var Cookie = {
  Create: function(name, value, days){
    var expires = "";
    if(days){
      var date = new Date();
      date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
      expires = "; expires=" + date.toGMTString();
    }
    document.cookie = name + "=" + value + expires + "; path=/";
  },
  Read: function(name){
    var nameEQ = name + "=";
    var ca = document.cookie.split(";");
    for(var i = 0; i < ca.length; i++){
      var c = ca[i];
      while(c.charAt(0) == " ") c = c.substring(1, c.length);
      if(c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
  },
  Erase: function(name){
    Cookie.Create(name, "", -1);
  }
};

dialog= function(content, onconfirm, oncancel) {
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

var DATES = ["January", "April", "September"];
var EXAM_MTH = "January";
var EXAM_DAY = 15;

function date_warning(){
  moment.locale("en");

  for (i in DATES){
    var month = DATES[i];
    var day = moment().month(month).daysInMonth();
    var end = moment().month(month).date(day);
    if(moment().isSameOrBefore(end)){
      break;
    }
  }
  var end_date = end.format("Do of MMMM");
  var exam_date = end.add(EXAM_DAY, "days").format("Do of MMMM YYYY");
  var fin_date = moment().add(1, "years").format("YYYY");

  return "Request submitted before the {0} will be examined the {1}.".f(end_date, exam_date);
}

function end_warning(){
  var start = moment().month(1).date(15).format(); // First session in February
  var end = moment().month(9).date(30).format(); // Last session in Septembre
  var between = moment().isBetween(start, end);
  var prefix = (between) ? "Additional" : "Allocated";
  var year = moment().add(1, "years").format("YYYY");
  return prefix + " resources must be used before <b>the end of February {0}</b>.".f(year);
}


(function(window, document, $, undefined){
  "use strict";
  window.contact = "mesocentre-techn@univ-amu.fr";
  window.proj = {};
  window.proj.url = {
    add: "user/new",
    assign: "user/assign",
    extend: "project/extend",
    delete: "project/delete/user",
    history: "project/history",
    activate: "project/reactivate",
    transform: "project/transform"
  };
  window.proj.send = function(url, data){
    var modal = UIkit.modal.blockUI("Sending data...");
    return $.ajax({
      contentType: "application/json",
      data: JSON.stringify(data),
      dataType: "json",
      timeout: 5000,
      type: "POST",
      url: window.proj.url[url]
    }).done(function(resp){
      UIkit.notify("Data exchange finished successfully", {timeout: 2000, status:"success"});
    }).fail(function(request){
      window.error(request);
    }).always(function() {
      modal.hide();
    });
  }

  window.error = function(req){
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

  window.render = {};
  window.render.input_empty = function(){
    $(this).val().length < 1 ? $(this).addClass("uk-form-danger") : $(this).removeClass("uk-form-danger");
  };

  window.render.check_data = function(data){
    var result = true;
    $.each(data, function(key, value){
      if(value.length < 1){
        result = false;
        return false;
      }
    });
    return result
  };

  window.render.check_positive = function(is_num, message){
    var msg = "{0} must be a positive number".f(message)
    if(!/^\d+$/.test(is_num)){
      alert(msg);
      return false;
    }
    return true;
  }
  window.render.paint_red = function(data){
    $.each(data, function(key, value){
      if(value.length < 1){
        $("[name={0}]".f(key)).addClass("uk-form-danger");
      }
    });
  }
  window.render.new_user = function(e){
    var name = $(this).data("name");
    var id = $(this).data("project");
    var title = "Create new user for the project {0}?".f(name);
    var name = $("<input/>").addClass("uk-width-1-1").attr({
      "name": "name",
      "type": "text",
      "placeholder": "Name"
    });
    var surname = $("<input/>").addClass("uk-width-1-1").attr({
      "name": "surname",
      "type": "text",
      "placeholder": "Surname"
    });
    var mail = $("<input/>").addClass("uk-width-1-1").attr({
      "name": "email",
      "type": "email",
      "placeholder": "e-mail"
    });
    var form = $("<form/>").addClass("uk-form").append(
            $("<legend/>").text(title)
        ).append(
            $("<div/>").addClass("uk-form-row").append(name)
        ).append(
            $("<div/>").addClass("uk-form-row").append(surname)
        ).append(
            $("<div/>").addClass("uk-form-row").append(mail)
        ).append(
            $("<div>Please double check if indicated e-mail is correct</div>").addClass("uk-form-row uk-alert")
        );
    dialog(form.prop("outerHTML"), function(){
      var data = {
        "name": $("input[name=name]").val(),
        "surname": $("input[name=surname]").val(),
        "email": $("input[name=email]").val(),
        "project": id
      };
      window.render.paint_red(data);
      if(!window.render.check_data(data)){
        return false;
      }
      window.proj.send("add", data);
      return true
    });
  }

  window.render.extend = function(e){
    var name = $(this).data("name");
    var id = $(this).data("project");
    var title = "Request additional CPU hours for the project {0}?".f(name);
    var placeholder = "Motivation:\nShort description of the request";
    var cpu = $("<input/>").addClass("uk-width-1-1").attr({
      "name": "cpu",
      "type": "text",
      "placeholder": "CPU hours"
    });
    var motiv = $("<textarea/>").addClass("uk-width-1-1").attr({
        "rows": "4",
        "name": "note",
        "placeholder": placeholder
      })
    var express = $("<div/>").addClass("uk-form-row uk-alert uk-alert-danger").text(
        "For any exceptional extension, send a mail directly to: mesocentre-aap@univ-amu.fr");
    var warn = "<div>" + date_warning() + "</div><div>" + end_warning() + "</div>";
    var form = $("<form/>").addClass("uk-form").append(
            $("<legend/>").text(title)
        ).append(
          express
        ).append(
          $("<div/>").addClass("uk-form-row").append(cpu)
        ).append(
          $("<div/>").addClass("uk-form-row").append(motiv)
        ).append(
          $("<div>{0}</div>".f(warn)).addClass("uk-form-row uk-alert")
        );
    dialog(form.prop("outerHTML"), function(){
      var data = {
        "cpu": $("input[name=cpu]").val(),
        "note": $("textarea[name=note]").val(),
        "project": id
      };
      window.render.paint_red(data);
      if(!window.render.check_data(data)){
        return false;
      }
      if(!window.render.check_positive(data["cpu"], "CPU hours")){
        return false;
      }
      window.proj.send("extend", data);
      return true;
    });
  }

  window.render.transform_project = function(e){
    var name = $(this).data("name");
    var id = $(this).data("project");
    var title = "Transform existing project {0} to type B ?".f(name);
    var placeholder = "Motivation:\nShort description of the request";
    var motiv = $("<textarea/>").addClass("uk-width-1-1").attr({
        "rows": "4",
        "name": "note",
        "placeholder": placeholder
      })
    var form = $("<form/>").addClass("uk-form").append(
            $("<legend/>").text(title)
        ).append(
          $("<div/>").addClass("uk-form-row").append(motiv)
        );
    dialog(form.prop("outerHTML"), function(){
      var data = {
        "note": $("textarea[name=note]").val(),
        "project": id
      };
      window.render.paint_red(data);
      if(!window.render.check_data(data)){
        return false;
      }
      window.proj.send("transform", data).done(function(){
        $(".trans").attr("disabled", true);
        Cookie.Create("project_transform", true, 30);
      });
      return true;
    });
  }

  window.render.activate_project = function(e){
    var name = $(this).data("name");
    var id = $(this).data("project");
    var title = "Re-activate existing project {0}?".f(name);
    var placeholder = "Motivation:\nShort description of the request";
    var motiv = $("<textarea/>").addClass("uk-width-1-1").attr({
        "rows": "4",
        "name": "note",
        "placeholder": placeholder
      })
    var form = $("<form/>").addClass("uk-form").append(
            $("<legend/>").text(title)
        ).append(
          $("<div/>").addClass("uk-form-row").append(motiv)
        );
    dialog(form.prop("outerHTML"), function(){
      var data = {
        "note": $("textarea[name=note]").val(),
        "project": id
      };
      window.render.paint_red(data);
      if(!window.render.check_data(data)){
        return false;
      }
      window.proj.send("activate", data).done(function(){
        $(".react").attr("disabled", true);
        Cookie.Create("project_active", true, 30);
      });
      return true;
    });
  }

  window.render.btn_reshuffle = function(proj, login){
    var id = "#{0}_{1}".f(proj, login);
    var prnt = $(id).parent("div");
    $(id).remove();

    var btns = prnt.find("button");
    if(btns.length == 1){
      btns[0].remove();
    }
  }

  window.render.remove_user = function(e){
    var id = $(this).data("pid");
    var full = $(this).data("name");
    var login = $(this).data("login");
    var name = $(this).data("project");
    var txt = "Are you sure you want to remove {0} from the project {1}?".f(full, name);
    var data = {"project": id, "login": login};
    UIkit.modal.confirm(txt, function(){
      window.proj.send("delete", data).done(function(reply){
        window.render.user_reshuffle(reply.data, name, id);
      });
    });
  }

  window.render.assign_user = function(e){
    var name = $(this).data("name");
    var id = $(this).data("project");
    var title = "Assign a new user to the project {0}?".f(name);
    var input = $("<input>").addClass("uk-width-1-1").attr({
        "type": "text",
        "name": "assign",
        "placeholder": "Enter the login name of an already registered user"
      })
    var form = $("<form/>").addClass("uk-form").append(
            $("<legend/>").text(title)
        ).append(
          $("<div/>").addClass("uk-form-row").append(input)
        );
    dialog(form.prop("outerHTML"), function(){
      var data = {
        "login": $("input[name=assign]").val(),
        "project": id
      };
      window.render.paint_red(data);
      if(!window.render.check_data(data)){
        return false;
      }
      window.proj.send("assign", data).done(function(reply){
        window.render.user_reshuffle(reply.data, name, id);
      });
      return true;
    });
  }
  window.render.del_button = function(project, user){
    var btn = $("<button/>").attr({
        "type": "button",
        "data-pid": project.id,
        "data-name": user.fullname,
        "data-login": user.login,
        "data-project": project.name
        });
    if(!user.responsible){
      btn.addClass("uk-button uk-button-mini uk-button-link uk-text-danger remove uk-icon-justify");
      btn.append($("<span/>").addClass("uk-icon-close"));
    }else{
      btn.addClass("uk-button uk-button-mini uk-button-link uk-icon-justify");
      btn.prop("disabled",true);
    }
    return btn
  }
  window.render.user_reshuffle = function(users, proj_name, proj_id){
    $("#project_users").empty();
    users.sort(function(a,b){
      if(a.fullname < b.fullname)
              return -1;
      if(a.fullname > b.fullname)
              return 1;
      return 0;
    });
    $.each(users, function(idx, value){
      var btn = window.render.del_button({id: proj_id, name: proj_name}, value)
      var id = "{0}_{1}".f(proj_name, value.login);
      var info = "{0}: {1}".f(value.fullname, value.consumption);
      var div = $("<div/>").addClass("uk-panel").attr({"id": id}).append(
        btn
      ).append(
        $("<span/>").addClass("uk-margin-small-left").text(info)
      );
      $("#project_users").append(div);
    });
  }
  window.render.history = function(data, title){
    var info = $("<table/>").addClass(
          "uk-table uk-table-striped uk-table-condensed");
    data.sort(function(a,b){
      return new Date(b.date) - new Date(a.date);
    });
    data.forEach(function(user){
      var tr = $("<tr>");
      ["date", "message"].forEach(function(attr){
        var txt = user[attr];
        txt = txt.replace(/</g, "&lt;");
        txt = txt.replace(/>/g, "&gt;");
        tr.append("<td>" + txt + "</td>");
      });
      info.append(tr);
    });

    $("#modal_body").html(info.prop("outerHTML"));

    var modal = UIkit.modal("#modal");
    if ( modal.isActive() ) {
        modal.hide();
    } else {
        modal.show();
    }

  }
  window.render.project_history = function(e){
    var name = $(this).data("name");
    var id = $(this).data("project");
    var title = "History for project {0}".f(name);
    var data = {"project": id};
    window.proj.send("history", data).done(function(reply){
      if(reply.length > 0){
        window.render.history(reply, title);
      }else{
        UIkit.modal.alert("No history found for project {0}".f(name));
      }
    })
  }

  $(document).on("click", ".new", window.render.new_user);
  $(document).on("click", ".assign", window.render.assign_user);
  $(document).on("click", ".extend", window.render.extend);
  $(document).on("click", ".renew", window.render.extend);
  $(document).on("click", ".history", window.render.project_history);
  $(document).on("click", ".react", window.render.activate_project);
  $(document).on("click", ".trans", window.render.transform_project);
  $(document).on("click", ".remove", window.render.remove_user); //the buttons could be created on the fly

  $(document).on("blur", "input,textarea", window.render.input_empty);
  $(document).on("ready", function(){
    var active = Cookie.Read("project_active");
    if(active){
      $(".react").attr("disabled", true);
    }
    var trans = Cookie.Read("project_transform");
    if(trans){
        $(".trans").attr("disabled", true);
    }
  });
})(window, document, jQuery);