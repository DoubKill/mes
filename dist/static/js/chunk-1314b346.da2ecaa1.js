(window["webpackJsonp"]=window["webpackJsonp"]||[]).push([["chunk-1314b346"],{1:function(t,e){},2:function(t,e){},2275:function(t,e,n){"use strict";n.r(e);var a=function(){var t=this,e=t.$createElement,n=t._self._c||e;return n("div",{staticClass:"app-container"},[n("el-form",{attrs:{inline:!0}},[n("el-form-item",{attrs:{label:"类型"}},[n("el-select",{attrs:{multiple:"",placeholder:"请选择"},on:{change:t.getTableData,"visible-change":t.visibleChange},model:{value:t.getParams.type_name,callback:function(e){t.$set(t.getParams,"type_name",e)},expression:"getParams.type_name"}},t._l(t.typeOptions,(function(t){return n("el-option",{key:t.global_name,attrs:{label:t.global_name,value:t.global_name}})})),1)],1),n("el-form-item",{attrs:{label:"库存位"}},[n("inventoryPosition",{on:{changSelect:t.changSelect}})],1),n("el-form-item",{staticStyle:{float:"right"}},[n("el-button",{on:{click:t.showCreateDialog}},[t._v("新建")])],1)],1),n("el-table",{staticStyle:{width:"100%"},attrs:{data:t.tableData,border:"","highlight-current-row":""}},[n("el-table-column",{attrs:{align:"center",type:"index",label:"No",width:"50"}}),n("el-table-column",{attrs:{prop:"type_name",label:"类型"}}),n("el-table-column",{attrs:{prop:"name",label:"库存位"}}),n("el-table-column",{attrs:{label:"操作"},scopedSlots:t._u([{key:"default",fn:function(e){return[n("el-button-group",[n("el-button",{attrs:{size:"mini"},on:{click:function(n){return t.showEditDialog(e.row)}}},[t._v("编辑")]),n("el-button",{attrs:{size:"mini",type:"danger"},on:{click:function(n){return t.handleDelete(e.row)}}},[t._v(t._s(e.row.used_flag?"停用":"启用")+" ")])],1)]}}])})],1),n("page",{attrs:{"old-page":!1,total:t.total,"current-page":t.getParams.page},on:{currentChange:t.currentChange}}),n("el-dialog",{attrs:{title:"添加位置点",visible:t.dialogCreateVisible,"close-on-click-modal":!1},on:{"update:visible":function(e){t.dialogCreateVisible=e}}},[n("el-form",{ref:"createForm",attrs:{rules:t.rules,model:t.locationForm}},[n("el-form-item",{attrs:{label:"类型"}},[n("el-select",{attrs:{placeholder:"请选择"},model:{value:t.locationForm.type,callback:function(e){t.$set(t.locationForm,"type",e)},expression:"locationForm.type"}},t._l(t.typeOptions,(function(t){return n("el-option",{key:t.id,attrs:{label:t.global_name,value:t.id}})})),1)],1),n("el-form-item",{attrs:{label:"位置点",prop:"name"}},[n("el-input",{model:{value:t.locationForm.name,callback:function(e){t.$set(t.locationForm,"name",e)},expression:"locationForm.name"}})],1)],1),n("div",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[n("el-button",{on:{click:function(e){t.dialogCreateVisible=!1}}},[t._v("取 消")]),n("el-button",{attrs:{type:"primary"},on:{click:t.handleCreate}},[t._v("确 定")])],1)],1),n("el-dialog",{attrs:{title:"编辑位置点",visible:t.dialogEditVisible,"close-on-click-modal":!1},on:{"update:visible":function(e){t.dialogEditVisible=e}}},[n("el-form",{ref:"editForm",attrs:{rules:t.rules,model:t.locationForm}},[n("el-form-item",{attrs:{label:"类型"}},[n("el-select",{attrs:{placeholder:"请选择"},model:{value:t.locationForm.type,callback:function(e){t.$set(t.locationForm,"type",e)},expression:"locationForm.type"}},t._l(t.typeOptions,(function(t){return n("el-option",{key:t.id,attrs:{label:t.global_name,value:t.id}})})),1)],1),n("el-form-item",{attrs:{label:"位置点",prop:"name"}},[n("el-input",{model:{value:t.locationForm.name,callback:function(e){t.$set(t.locationForm,"name",e)},expression:"locationForm.name"}})],1)],1),n("div",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[n("el-button",{on:{click:function(e){t.dialogEditVisible=!1}}},[t._v("取 消")]),n("el-button",{attrs:{type:"primary"},on:{click:t.handleEdit}},[t._v("确 定")])],1)],1)],1)},o=[],r=(n("b0c0"),n("b775")),i=n("99b1");function l(t){return Object(r["a"])({url:i["a"].SpareLocation,method:"get",params:t})}function c(t){return Object(r["a"])({url:i["a"].SpareLocation,method:"post",data:t})}function u(t,e){return Object(r["a"])({url:i["a"].SpareLocation+e+"/",method:"put",data:t})}function s(t){return Object(r["a"])({url:i["a"].SpareLocation+t+"/",method:"delete"})}var d=n("8041"),m=n("3e51"),f=n("6336"),b=n("ed08"),p={components:{inventoryPosition:d["a"],page:m["a"]},data:function(){return{formLabelWidth:"auto",tableData:[],typeOptions:[],types:[],dialogCreateVisible:!1,dialogEditVisible:!1,locationForm:{type:"",name:""},rules:{name:[{required:!0,message:"不能为空",trigger:"blur"}]},getParams:{page:1,type_name:[],name:""},currentPage:1,total:1}},created:function(){this.getTableData()},methods:{getTableData:function(){var t=this;l(this.getParams).then((function(e){t.tableData=e.results,t.total=e.count}))},changSelect:function(t){this.getParams.name=t?t.name:"",this.getParams.page=1,this.getTableData()},getTypeOptions:function(){var t=this;Object(f["c"])({all:1,class_name:"备品备件类型"}).then((function(e){t.typeOptions=e.results}))},visibleChange:function(t){t&&this.getTypeOptions()},showCreateDialog:function(){var t=this;this.getTypeOptions(),this.locationForm={type:"",name:""},this.dialogCreateVisible=!0,this.$nextTick((function(){t.$refs.createForm.clearValidate()}))},handleCreate:function(){var t=this;this.$refs.createForm.validate((function(e){e&&c(t.locationForm).then((function(e){t.dialogCreateVisible=!1,t.$message(t.locationForm.name+"创建成功"),t.getTableData()})).catch((function(e){Object(b["c"])(t,e)}))}))},showEditDialog:function(t){var e=this;this.getTypeOptions(),this.locationForm=Object.assign({},t),this.dialogEditVisible=!0,this.$nextTick((function(){e.$refs.editForm.clearValidate()}))},handleEdit:function(){var t=this;this.$refs.editForm.validate((function(e){e&&u(t.locationForm,t.locationForm.id).then((function(e){t.dialogEditVisible=!1,t.$message(t.locationForm.name+"修改成功"),t.getTableData()}))}))},handleDelete:function(t){var e=this,n=t.used_flag?"停用":"启用";this.$confirm("此操作将"+n+t.name+", 是否继续?","提示",{confirmButtonText:"确定",cancelButtonText:"取消",type:"warning"}).then((function(){s(t.id).then((function(t){e.$message({type:"success",message:"操作成功!"}),e.getTableData()}))}))},currentChange:function(t,e){this.getParams.page=t,this.getParams.page_size=e,this.getTableData()}}},g=p,h=n("2877"),v=Object(h["a"])(g,a,o,!1,null,null,null);e["default"]=v.exports},3:function(t,e){},6336:function(t,e,n){"use strict";n.d(e,"d",(function(){return r})),n.d(e,"f",(function(){return i})),n.d(e,"h",(function(){return l})),n.d(e,"b",(function(){return c})),n.d(e,"c",(function(){return u})),n.d(e,"e",(function(){return s})),n.d(e,"g",(function(){return d})),n.d(e,"a",(function(){return m}));var a=n("b775"),o=n("99b1");function r(t){return Object(a["a"])({url:o["a"].GlobalTypesUrl,method:"get",params:t})}function i(t){return Object(a["a"])({url:o["a"].GlobalTypesUrl,method:"post",data:t})}function l(t,e){return Object(a["a"])({url:o["a"].GlobalTypesUrl+e+"/",method:"put",data:t})}function c(t){return Object(a["a"])({url:o["a"].GlobalTypesUrl+t+"/",method:"delete"})}function u(t){return Object(a["a"])({url:o["a"].GlobalCodesUrl,method:"get",params:t})}function s(t){return Object(a["a"])({url:o["a"].GlobalCodesUrl,method:"post",data:t})}function d(t,e){return Object(a["a"])({url:o["a"].GlobalCodesUrl+e+"/",method:"put",data:t})}function m(t){return Object(a["a"])({url:o["a"].GlobalCodesUrl+t+"/",method:"delete"})}},"6dfa":function(t,e,n){"use strict";n.d(e,"b",(function(){return r})),n.d(e,"c",(function(){return i})),n.d(e,"d",(function(){return l})),n.d(e,"a",(function(){return c}));var a=n("b775"),o=n("99b1");function r(t){return Object(a["a"])({url:o["a"].MaterialLocationBinding,method:"get",params:t})}function i(t){return Object(a["a"])({url:o["a"].MaterialLocationBinding,method:"post",data:t})}function l(t,e){return Object(a["a"])({url:o["a"].MaterialLocationBinding+e+"/",method:"put",data:t})}function c(t){return Object(a["a"])({url:o["a"].MaterialLocationBinding+t+"/",method:"delete"})}},d585:function(t,e,n){"use strict";n.d(e,"a",(function(){return r})),n.d(e,"e",(function(){return i})),n.d(e,"g",(function(){return l})),n.d(e,"c",(function(){return c})),n.d(e,"f",(function(){return u})),n.d(e,"b",(function(){return s})),n.d(e,"i",(function(){return d})),n.d(e,"h",(function(){return m})),n.d(e,"d",(function(){return f}));var a=n("b775"),o=n("99b1");function r(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},r={url:e?o["a"].LocationNameList+e+"/":o["a"].LocationNameList,method:t};return Object.assign(r,n),Object(a["a"])(r)}function i(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},r={url:e?o["a"].SpareInventory+e+"/":o["a"].SpareInventory,method:t};return Object.assign(r,n),Object(a["a"])(r)}function l(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},r={url:(e?o["a"].SpareInventory+e+"/":o["a"].SpareInventory)+"check_storage/",method:t};return Object.assign(r,n),Object(a["a"])(r)}function c(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},r={url:(e?o["a"].SpareInventory+e+"/":o["a"].SpareInventory)+"put_storage/",method:t};return Object.assign(r,n),Object(a["a"])(r)}function u(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},r={url:e?o["a"].SpareInventoryLog+e+"/":o["a"].SpareInventoryLog,method:t};return Object.assign(r,n),Object(a["a"])(r)}function s(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},r={url:(e?o["a"].SpareInventory+e+"/":o["a"].SpareInventory)+"out_storage/",method:t};return Object.assign(r,n),Object(a["a"])(r)}function d(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},r={url:e?o["a"].SparepartsSpareType+e+"/":o["a"].SparepartsSpareType,method:t};return Object.assign(r,n),Object(a["a"])(r)}function m(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},r={url:e?o["a"].SparepartsSpare+e+"/":o["a"].SparepartsSpare,method:t};return Object.assign(r,n),Object(a["a"])(r)}function f(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},r={url:(e?o["a"].SpareInventoryLog+e+"/":o["a"].SpareInventoryLog)+"revocation_log/",method:t};return Object.assign(r,n),Object(a["a"])(r)}},ed08:function(t,e,n){"use strict";n.d(e,"e",(function(){return u})),n.d(e,"b",(function(){return d})),n.d(e,"a",(function(){return m})),n.d(e,"d",(function(){return f})),n.d(e,"c",(function(){return b}));n("4160"),n("caad"),n("c975"),n("45fc"),n("a9e3"),n("b64b"),n("d3b7"),n("4d63"),n("ac1f"),n("25f0"),n("2532"),n("4d90"),n("5319"),n("1276"),n("159b");var a=n("53ca"),o=n("4360"),r=n("ecc0"),i=n.n(r),l=n("d85b"),c=n.n(l);function u(t,e,n){var a=t?new Date(t):new Date,o={y:a.getFullYear(),m:s(a.getMonth()+1),d:s(a.getDate()),h:s(a.getHours()),i:s(a.getMinutes()),s:s(a.getSeconds()),a:s(a.getDay())};return e?o.y+"-"+o.m+"-"+o.d+" "+o.h+":"+o.i+":"+o.s:n&&"continuation"===n?o.y+o.m+o.d+o.h+o.i+o.s:o.y+"-"+o.m+"-"+o.d}function s(t){return t=Number(t),t<10?"0"+t:t}function d(t){if(!t&&"object"!==Object(a["a"])(t))throw new Error("error arguments","deepClone");var e=t.constructor===Array?[]:{};return Object.keys(t).forEach((function(n){t[n]&&"object"===Object(a["a"])(t[n])?e[n]=d(t[n]):e[n]=t[n]})),e}function m(t){if(t&&t instanceof Array&&t.length>0){var e=o["a"].getters&&o["a"].getters.permission,n=e[t[0]];if(!n||0===n.length)return;var a=n.some((function(e){return e===t[1]}));return a}return console.error("need roles! Like v-permission=\"['admin','editor']\""),!1}function f(t){var e=c.a.utils.table_to_book(document.querySelector("#out-table"),{raw:!0}),n=c.a.write(e,{bookType:"xlsx",bookSST:!0,type:"array"});try{i.a.saveAs(new Blob([n],{type:"application/octet-stream"}),t+".xlsx")}catch(a){"undefined"!==typeof console&&console.log(a,n)}return n}function b(t,e){if(t.$message.closeAll(),"[object Object]"===Object.prototype.toString.call(e)){var n="";for(var a in e)console.log(e[a]),e[a].forEach((function(t){n+=t}));n.includes("已存在")&&t.$message.error("已存在!")}}}}]);