(window["webpackJsonp"]=window["webpackJsonp"]||[]).push([["chunk-92a5bb62"],{7156:function(e,t,r){var i=r("861d"),n=r("d2bb");e.exports=function(e,t,r){var a,o;return n&&"function"==typeof(a=t.constructor)&&a!==r&&i(o=a.prototype)&&o!==r.prototype&&n(e,o),e}},"7e633":function(e,t,r){"use strict";r.d(t,"a",(function(){return a})),r.d(t,"e",(function(){return o})),r.d(t,"f",(function(){return u})),r.d(t,"d",(function(){return l})),r.d(t,"c",(function(){return s})),r.d(t,"b",(function(){return p}));var i=r("b775"),n=r("99b1");function a(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:null,r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},a="";a=t?n["a"].EquipCategoryUrl+t+"/":n["a"].EquipCategoryUrl;var o={url:a,method:e};return Object.assign(o,r),Object(i["a"])(o)}function o(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},r={url:n["a"].EquipTypeGlobalUrl,method:e};return Object.assign(r,t),Object(i["a"])(r)}function u(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},r={url:n["a"].EquipProcessGlobalUrl,method:e};return Object.assign(r,t),Object(i["a"])(r)}function l(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:null,r=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},a="";a=t?n["a"].EquipUrl+t+"/":n["a"].EquipUrl;var o={url:a,method:e};return Object.assign(o,r),Object(i["a"])(o)}function s(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},r={url:n["a"].EquipLevelGlobalUrl,method:e};return Object.assign(r,t),Object(i["a"])(r)}function p(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},r={url:n["a"].EquipCategoryUrl+"?all=1",method:e};return Object.assign(r,t),Object(i["a"])(r)}},a9e3:function(e,t,r){"use strict";var i=r("83ab"),n=r("da84"),a=r("94ca"),o=r("6eeb"),u=r("5135"),l=r("c6b6"),s=r("7156"),p=r("c04e"),c=r("d039"),d=r("7c73"),m=r("241c").f,f=r("06cf").f,g=r("9bf2").f,q=r("58a8").trim,b="Number",_=n[b],h=_.prototype,E=l(d(h))==b,v=function(e){var t,r,i,n,a,o,u,l,s=p(e,!1);if("string"==typeof s&&s.length>2)if(s=q(s),t=s.charCodeAt(0),43===t||45===t){if(r=s.charCodeAt(2),88===r||120===r)return NaN}else if(48===t){switch(s.charCodeAt(1)){case 66:case 98:i=2,n=49;break;case 79:case 111:i=8,n=55;break;default:return+s}for(a=s.slice(2),o=a.length,u=0;u<o;u++)if(l=a.charCodeAt(u),l<48||l>n)return NaN;return parseInt(a,i)}return+s};if(a(b,!_(" 0o1")||!_("0b1")||_("+0x1"))){for(var y,F=function(e){var t=arguments.length<1?0:e,r=this;return r instanceof F&&(E?c((function(){h.valueOf.call(r)})):l(r)!=b)?s(new _(v(t)),r,F):v(t)},w=i?m(_):"MAX_VALUE,MIN_VALUE,NaN,NEGATIVE_INFINITY,POSITIVE_INFINITY,EPSILON,isFinite,isInteger,isNaN,isSafeInteger,MAX_SAFE_INTEGER,MIN_SAFE_INTEGER,parseFloat,parseInt,isInteger".split(","),O=0;w.length>O;O++)u(_,y=w[O])&&!u(F,y)&&g(F,y,f(_,y));F.prototype=h,h.constructor=F,o(n,b,F)}},c7f3:function(e,t,r){"use strict";r.r(t);var i=function(){var e=this,t=e.$createElement,r=e._self._c||t;return r("div",[r("el-form",{attrs:{inline:!0}},[r("el-form-item",{attrs:{label:"工序"}},[r("el-input",{on:{input:e.changeSearch},model:{value:e.process,callback:function(t){e.process=e._n(t)},expression:"process"}})],1),r("el-form-item",{attrs:{label:"设备名"}},[r("el-input",{on:{input:e.changeSearch},model:{value:e.equip,callback:function(t){e.equip=t},expression:"equip"}})],1),r("el-form-item",[e.permissionObj.equip&&e.permissionObj.equip.indexOf("add")>-1?r("el-button",{on:{click:e.showCreateEquipDialog}},[e._v("新建")]):e._e()],1)],1),r("el-table",{staticStyle:{width:"100%"},attrs:{data:e.tableData,border:""}},[r("el-table-column",{attrs:{align:"center",type:"index",label:"No",width:"50"}}),r("el-table-column",{attrs:{align:"center",prop:"equip_no",label:"设备代码"}}),r("el-table-column",{attrs:{align:"center",width:"200%",prop:"equip_name",label:"设备名称"}}),r("el-table-column",{attrs:{align:"center",prop:"equip_type",label:"设备类型"}}),r("el-table-column",{attrs:{align:"center",width:"100",prop:"equip_process_no",label:"工序代码"}}),r("el-table-column",{attrs:{align:"center",prop:"equip_process_name",label:"工序名称"}}),r("el-table-column",{attrs:{align:"center",prop:"category_no",label:"机型编号"}}),r("el-table-column",{attrs:{align:"center",prop:"category_name",label:"机型名称"}}),r("el-table-column",{attrs:{align:"center",width:"50",prop:"equip_level_name",label:"设备层级"}}),r("el-table-column",{attrs:{align:"center",width:"50",prop:"count_flag",label:"产量计数",formatter:e.EquipCountFlagFormatter}}),r("el-table-column",{attrs:{align:"center",prop:"description",label:"备注"}}),r("el-table-column",{attrs:{align:"center",width:"50",prop:"use_flag",label:"是否启用",formatter:e.EquipUsedFlagFormatter}}),r("el-table-column",{attrs:{align:"center",label:"操作"},scopedSlots:e._u([{key:"default",fn:function(t){return[r("el-button-group",[e.permissionObj.equip&&e.permissionObj.equip.indexOf("change")>-1?r("el-button",{attrs:{size:"mini"},on:{click:function(r){return e.showEditEquipDialog(t.row)}}},[e._v("编辑 ")]):e._e(),e.permissionObj.equip&&e.permissionObj.equip.indexOf("delete")>-1?r("el-button",{attrs:{size:"mini",type:"danger"},on:{click:function(r){return e.handleEquipDelete(t.row)}}},[e._v(e._s(t.row.use_flag?"停用":"启用")+" ")]):e._e()],1)]}}])})],1),r("page",{attrs:{total:e.total,"current-page":e.getParams.page},on:{currentChange:e.currentChange}}),r("el-dialog",{attrs:{title:"添加设备基础信息",visible:e.dialogCreateEquipVisible},on:{"update:visible":function(t){e.dialogCreateEquipVisible=t}}},[r("el-form",{ref:"AddEquipForm",attrs:{model:e.AddEquipForm,rules:e.add_equip_rules}},[r("el-form-item",{attrs:{label:"设备编号",prop:"equip_no"}},[r("el-input",{model:{value:e.AddEquipForm.equip_no,callback:function(t){e.$set(e.AddEquipForm,"equip_no",t)},expression:"AddEquipForm.equip_no"}})],1),r("el-form-item",{attrs:{label:"设备名称",prop:"equip_name"}},[r("el-input",{model:{value:e.AddEquipForm.equip_name,callback:function(t){e.$set(e.AddEquipForm,"equip_name",t)},expression:"AddEquipForm.equip_name"}})],1),r("el-form-item",{attrs:{label:"产量计数"}},[r("el-switch",{model:{value:e.AddEquipForm.count_flag,callback:function(t){e.$set(e.AddEquipForm,"count_flag",t)},expression:"AddEquipForm.count_flag"}})],1),r("el-form-item",{attrs:{label:"备注"}},[r("el-input",{model:{value:e.AddEquipForm.description,callback:function(t){e.$set(e.AddEquipForm,"description",t)},expression:"AddEquipForm.description"}})],1),r("el-form-item",{attrs:{label:"设备层级",prop:"equip_level"}},[r("el-select",{staticStyle:{width:"100%"},attrs:{placeholder:"请选择"},on:{"visible-change":e.shiftsEquipLevelChange},model:{value:e.AddEquipForm.equip_level,callback:function(t){e.$set(e.AddEquipForm,"equip_level",t)},expression:"AddEquipForm.equip_level"}},e._l(e.EquipLevelOptions,(function(e){return r("el-option",{key:e.id,attrs:{value:e.id,label:e.global_name}})})),1)],1),r("el-form-item",{attrs:{label:"设备种类",prop:"category"}},[r("el-select",{staticStyle:{width:"100%"},attrs:{placeholder:"请选择"},on:{"visible-change":e.shiftsEquipCategoryChange},model:{value:e.AddEquipForm.category,callback:function(t){e.$set(e.AddEquipForm,"category",t)},expression:"AddEquipForm.category"}},e._l(e.EquipCategoryOptions,(function(e){return r("el-option",{key:e.id,attrs:{value:e.value,label:e.label}})})),1)],1)],1),r("div",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[r("el-button",{on:{click:function(t){e.dialogCreateEquipVisible=!1}}},[e._v("取 消")]),r("el-button",{attrs:{type:"primary"},on:{click:function(t){return e.handleCreateEquip("AddEquipForm")}}},[e._v("确 定")])],1)],1),r("el-dialog",{attrs:{title:"编辑设备基础信息",visible:e.dialogEditEquipVisible},on:{"update:visible":function(t){e.dialogEditEquipVisible=t}}},[r("el-form",{ref:"ModifyEquipForm",attrs:{model:e.ModifyEquipForm,rules:e.modify_equip_rules}},[r("el-form-item",{attrs:{label:"设备编号",prop:"equip_no"}},[r("el-input",{attrs:{disabled:!0},model:{value:e.ModifyEquipForm.equip_no,callback:function(t){e.$set(e.ModifyEquipForm,"equip_no",t)},expression:"ModifyEquipForm.equip_no"}})],1),r("el-form-item",{attrs:{label:"设备名称",prop:"equip_name"}},[r("el-input",{model:{value:e.ModifyEquipForm.equip_name,callback:function(t){e.$set(e.ModifyEquipForm,"equip_name",t)},expression:"ModifyEquipForm.equip_name"}})],1),r("el-form-item",{attrs:{label:"产量计数"}},[r("el-switch",{model:{value:e.ModifyEquipForm.count_flag,callback:function(t){e.$set(e.ModifyEquipForm,"count_flag",t)},expression:"ModifyEquipForm.count_flag"}})],1),r("el-form-item",{attrs:{label:"备注"}},[r("el-input",{model:{value:e.ModifyEquipForm.description,callback:function(t){e.$set(e.ModifyEquipForm,"description",t)},expression:"ModifyEquipForm.description"}})],1),r("el-form-item",{attrs:{label:"设备层级",prop:"equip_level"}},[r("el-select",{staticStyle:{width:"100%"},attrs:{placeholder:"请选择"},on:{"visible-change":e.shiftsEquipLevelChange},model:{value:e.ModifyEquipForm.equip_level,callback:function(t){e.$set(e.ModifyEquipForm,"equip_level",t)},expression:"ModifyEquipForm.equip_level"}},e._l(e.EquipLevelOptions,(function(e){return r("el-option",{key:e.id,attrs:{value:e.id,label:e.global_name}})})),1)],1),r("el-form-item",{attrs:{label:"设备种类",prop:"category"}},[r("el-select",{staticStyle:{width:"100%"},attrs:{placeholder:"请选择"},on:{"visible-change":e.shiftsEquipCategoryChange},model:{value:e.ModifyEquipForm.category,callback:function(t){e.$set(e.ModifyEquipForm,"category",t)},expression:"ModifyEquipForm.category"}},e._l(e.EquipCategoryOptions,(function(e){return r("el-option",{key:e.id,attrs:{value:e.value,label:e.label}})})),1)],1)],1),r("div",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[r("el-button",{on:{click:function(t){e.dialogEditEquipVisible=!1}}},[e._v("取 消")]),r("el-button",{attrs:{type:"primary"},on:{click:function(t){return e.handleEditEquip("ModifyEquipForm")}}},[e._v("确 定")])],1)],1)],1)},n=[],a=(r("a4d3"),r("e01a"),r("96cf"),r("1da1")),o=r("5530"),u=r("3e51"),l=r("7e633"),s=r("2f62"),p={components:{page:u["a"]},computed:Object(o["a"])({},Object(s["b"])(["permission"])),data:function(){return{tableData:[],total:0,getParams:{page:1},process:null,equip:null,EquipLevel:[],EquipLevelOptions:[],equip_level:"",EquipCategory:[],EquipCategoryOptions:[],category:"",AddEquipForm:{equip_no:"",equip_name:"",count_flag:!0,use_flag:!0,description:"",equip_level:"",category:""},ModifyEquipForm:{equip_no:"",equip_name:"",count_flag:!0,use_flag:!0,description:"",equip_level:"",category:""},add_equip_rules:{equip_no:[{required:!0,message:"请输入设备编号",trigger:"blur"}],equip_name:[{required:!0,message:"请输入设备名称",trigger:"blur"}],equip_level:[{required:!0,message:"请选择设备层级",trigger:"change"}],category:[{required:!0,message:"请选择设备种类",trigger:"change"}]},modify_equip_rules:{equip_no:[{required:!0,message:"请输入设备编号",trigger:"blur"}],equip_name:[{required:!0,message:"请输入设备名称",trigger:"blur"}],equip_level:[{required:!0,message:"请选择设备层级",trigger:"change"}],category:[{required:!0,message:"请选择设备种类",trigger:"change"}]},EquipFormError:{equip_no:"",equip_name:"",count_flag:"",use_flag:"",description:"",equip_level:"",category:""},dialogCreateEquipVisible:!1,dialogEditEquipVisible:!1}},created:function(){this.permissionObj=this.permission,this.equip_manage_list()},methods:{equip_manage_list:function(){var e=this;return Object(a["a"])(regeneratorRuntime.mark((function t(){var r;return regeneratorRuntime.wrap((function(t){while(1)switch(t.prev=t.next){case 0:return t.prev=0,t.next=3,Object(l["d"])("get",null,{params:e.getParams});case 3:r=t.sent,e.tableData=r.results,e.total=r.count,t.next=11;break;case 8:throw t.prev=8,t.t0=t["catch"](0),new Error(t.t0);case 11:case"end":return t.stop()}}),t,null,[[0,8]])})))()},equip_manage_post:function(e){return Object(a["a"])(regeneratorRuntime.mark((function t(){var r;return regeneratorRuntime.wrap((function(t){while(1)switch(t.prev=t.next){case 0:return t.prev=0,t.next=3,Object(l["d"])("post",null,e);case 3:return r=t.sent,t.abrupt("return",r);case 7:throw t.prev=7,t.t0=t["catch"](0),new Error(t.t0);case 10:case"end":return t.stop()}}),t,null,[[0,7]])})))()},equip_manage_delete:function(e){return Object(a["a"])(regeneratorRuntime.mark((function t(){return regeneratorRuntime.wrap((function(t){while(1)switch(t.prev=t.next){case 0:return t.prev=0,t.next=3,Object(l["d"])("delete",e,{});case 3:t.next=8;break;case 5:throw t.prev=5,t.t0=t["catch"](0),new Error(t.t0);case 8:case"end":return t.stop()}}),t,null,[[0,5]])})))()},equip_manage_modify:function(e,t){return Object(a["a"])(regeneratorRuntime.mark((function r(){return regeneratorRuntime.wrap((function(r){while(1)switch(r.prev=r.next){case 0:return r.prev=0,r.next=3,Object(l["d"])("put",e,t);case 3:r.next=8;break;case 5:throw r.prev=5,r.t0=r["catch"](0),new Error(r.t0);case 8:case"end":return r.stop()}}),r,null,[[0,5]])})))()},equip_level_list:function(){var e=this;return Object(a["a"])(regeneratorRuntime.mark((function t(){var r;return regeneratorRuntime.wrap((function(t){while(1)switch(t.prev=t.next){case 0:return t.prev=0,t.next=3,Object(l["c"])("get",{params:{}});case 3:r=t.sent,0!==r.results.length&&(e.EquipLevelOptions=r.results),t.next=10;break;case 7:throw t.prev=7,t.t0=t["catch"](0),new Error(t.t0);case 10:case"end":return t.stop()}}),t,null,[[0,7]])})))()},equip_category_list:function(){var e=this;return Object(a["a"])(regeneratorRuntime.mark((function t(){var r,i,n;return regeneratorRuntime.wrap((function(t){while(1)switch(t.prev=t.next){case 0:return t.prev=0,t.next=3,Object(l["b"])("get",{params:{}});case 3:if(r=t.sent,0!==r.results.length)for(e.EquipCategory=r.results,i=0;i<e.EquipCategory.length;++i)n="设备类型: "+e.EquipCategory[i]["equip_type_name"]+";  机型名称: "+e.EquipCategory[i]["category_name"]+";  机型编号: "+e.EquipCategory[i]["category_no"]+";  工序: "+e.EquipCategory[i]["equip_process_name"],e.EquipCategoryOptions.push({key:e.EquipCategory[i]["id"],value:e.EquipCategory[i]["id"],label:n});t.next=10;break;case 7:throw t.prev=7,t.t0=t["catch"](0),new Error(t.t0);case 10:case"end":return t.stop()}}),t,null,[[0,7]])})))()},shiftsEquipLevelChange:function(e){e&&this.equip_level_list()},shiftsEquipCategoryChange:function(e){e&&this.equip_category_list()},processChanged:function(){},equipChanged:function(){},clearEquipForm:function(){this.EquipForm={equip_no:"",equip_name:"",count_flag:!0,use_flag:!0,description:"",equip_level:"",category:""}},clearEquipFormError:function(){this.EuqipFormError={equip_no:"",equip_name:"",count_flag:"",use_flag:"",description:"",equip_level:"",category:""}},showCreateEquipDialog:function(){this.clearEquipForm(),this.clearEquipFormError(),this.dialogCreateEquipVisible=!0},showEditEquipDialog:function(e){this.clearEquipForm(),this.clearEquipFormError(),this.equip_level_list(),this.equip_category_list(),this.ModifyEquipForm=Object.assign({},e),this.dialogEditEquipVisible=!0},handleEquipDelete:function(e){var t=this,r=e.use_flag?"停用":"启用";this.$confirm("此操作将"+r+e.equip_name+", 是否继续?","提示",{confirmButtonText:"确定",cancelButtonText:"取消",type:"warning"}).then((function(){try{Object(l["d"])("delete",e.id,{}).then((function(e){t.$message({type:"success",message:"操作成功!"}),t.equip_manage_list()}))}catch(r){}})).catch((function(){}))},handleCreateEquip:function(e){var t=this;this.$refs[e].validate(function(){var e=Object(a["a"])(regeneratorRuntime.mark((function e(r){return regeneratorRuntime.wrap((function(e){while(1)switch(e.prev=e.next){case 0:if(!r){e.next=14;break}return t.clearEquipForm(),e.prev=2,e.next=5,t.equip_manage_post({data:{category:t.AddEquipForm["category"],count_flag:t.AddEquipForm["count_flag"],description:t.AddEquipForm["description"],equip_level:t.AddEquipForm["equip_level"],equip_name:t.AddEquipForm["equip_name"],equip_no:t.AddEquipForm["equip_no"],use_flag:t.AddEquipForm["use_flag"]}});case 5:t.dialogCreateEquipVisible=!1,t.equip_manage_list(),e.next=12;break;case 9:e.prev=9,e.t0=e["catch"](2),e.t0;case 12:e.next=15;break;case 14:return e.abrupt("return",!1);case 15:case"end":return e.stop()}}),e,null,[[2,9]])})));return function(t){return e.apply(this,arguments)}}())},handleEditEquip:function(e){var t=this;this.$refs[e].validate(function(){var e=Object(a["a"])(regeneratorRuntime.mark((function e(r){return regeneratorRuntime.wrap((function(e){while(1)switch(e.prev=e.next){case 0:if(!r){e.next=13;break}return e.prev=1,e.next=4,t.equip_manage_modify(t.ModifyEquipForm.id,{data:{category:t.ModifyEquipForm["category"],count_flag:t.ModifyEquipForm["count_flag"],description:t.ModifyEquipForm["description"],equip_level:t.ModifyEquipForm["equip_level"],equip_name:t.ModifyEquipForm["equip_name"],equip_no:t.ModifyEquipForm["equip_no"],use_flag:t.ModifyEquipForm["use_flag"]}});case 4:t.dialogEditEquipVisible=!1,t.equip_manage_list(),e.next=11;break;case 8:e.prev=8,e.t0=e["catch"](1),e.t0;case 11:e.next=14;break;case 13:return e.abrupt("return",!1);case 14:case"end":return e.stop()}}),e,null,[[1,8]])})));return function(t){return e.apply(this,arguments)}}())},boolFormatter:function(e){return e?"Y":"N"},EquipCountFlagFormatter:function(e,t){return this.boolFormatter(e.count_flag)},EquipUsedFlagFormatter:function(e,t){return this.boolFormatter(e.use_flag)},changeSearch:function(){this.getParams["equip_process"]=this.process,this.getParams["equip_name"]=this.equip,this.getParams.page=1,this.equip_manage_list()},currentChange:function(e){this.getParams.page=e,this.equip_manage_list()}}},c=p,d=r("2877"),m=Object(d["a"])(c,i,n,!1,null,"501e71d1",null);t["default"]=m.exports},e01a:function(e,t,r){"use strict";var i=r("23e7"),n=r("83ab"),a=r("da84"),o=r("5135"),u=r("861d"),l=r("9bf2").f,s=r("e893"),p=a.Symbol;if(n&&"function"==typeof p&&(!("description"in p.prototype)||void 0!==p().description)){var c={},d=function(){var e=arguments.length<1||void 0===arguments[0]?void 0:String(arguments[0]),t=this instanceof d?new p(e):void 0===e?p():p(e);return""===e&&(c[t]=!0),t};s(d,p);var m=d.prototype=p.prototype;m.constructor=d;var f=m.toString,g="Symbol(test)"==String(p("test")),q=/^Symbol\((.*)\)[^)]+$/;l(m,"description",{configurable:!0,get:function(){var e=u(this)?this.valueOf():this,t=f.call(e);if(o(c,e))return"";var r=g?t.slice(7,-1):t.replace(q,"$1");return""===r?void 0:r}}),i({global:!0,forced:!0},{Symbol:d})}}}]);