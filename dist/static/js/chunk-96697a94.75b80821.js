(window["webpackJsonp"]=window["webpackJsonp"]||[]).push([["chunk-96697a94"],{"3be2":function(e,t,n){"use strict";n.r(t);var a=function(){var e=this,t=e.$createElement,n=e._self._c||t;return n("div",{directives:[{name:"loading",rawName:"v-loading",value:e.loading,expression:"loading"}]},[n("el-form",{attrs:{inline:!0,model:e.formInline}},[n("el-form-item",{attrs:{label:"时间"}},[n("el-date-picker",{attrs:{type:"date",placeholder:"选择日期","value-format":"yyyy-MM-dd"},model:{value:e.formInline.data,callback:function(t){e.$set(e.formInline,"data",t)},expression:"formInline.data"}})],1),n("el-form-item",{attrs:{label:"生产机型"}},[n("selectModel",{on:{selectChanged:e.selectModel}})],1),n("el-form-item",{attrs:{label:"小料配方编码"}},[n("el-input",{attrs:{placeholder:"请输入小料配方编码"},model:{value:e.formInline.input,callback:function(t){e.$set(e.formInline,"input",t)},expression:"formInline.input"}})],1),n("br"),n("el-form-item",{attrs:{label:"班次"}},[n("class-select",{on:{classSelected:e.classChanged}})],1),n("el-form-item",{attrs:{label:"配料设备"}},[n("selectBatchingEquip",{on:{selectChanged:e.selectBatchEquip}})],1),n("el-form-item",{attrs:{label:"状态"}},[n("el-input",{attrs:{placeholder:"请输入状态"},model:{value:e.formInline.state,callback:function(t){e.$set(e.formInline,"state",t)},expression:"formInline.state"}})],1)],1),n("el-table",{staticStyle:{width:"100%"},attrs:{data:e.tableData,border:""}},[n("el-table-column",{attrs:{type:"index",label:"No",width:"40"}}),n("el-table-column",{attrs:{prop:"date",label:"工厂时间"}}),n("el-table-column",{attrs:{prop:"name",label:"班次"}}),n("el-table-column",{attrs:{prop:"address",label:"小料配方编码"}}),n("el-table-column",{attrs:{prop:"date",label:"生产机型"}}),n("el-table-column",{attrs:{prop:"name",label:"配料设备"}}),n("el-table-column",{attrs:{prop:"address",label:"胶料编码"}}),n("el-table-column",{attrs:{prop:"date",label:"计划数量"}}),n("el-table-column",{attrs:{prop:"name",label:"明细查看"},scopedSlots:e._u([{key:"default",fn:function(t){return[n("el-button",{on:{click:function(n){return e.view(t.row,t.$index)}}},[e._v("查看")])]}}])}),n("el-table-column",{attrs:{prop:"address",label:"下发"},scopedSlots:e._u([{key:"default",fn:function(t){return[n("el-button",{on:{click:function(n){return e.sendOut(t.row,t.$index)}}},[e._v("发送")])]}}])}),n("el-table-column",{attrs:{prop:"date",label:"状态"}}),n("el-table-column",{attrs:{prop:"name",label:"下发人"}}),n("el-table-column",{attrs:{prop:"address",label:"下发时间"}})],1)],1)},r=[],l=(n("96cf"),n("1da1")),o=n("cfc4"),i=n("f9e3"),u=n("68de"),c={components:{classSelect:o["a"],selectModel:i["a"],selectBatchingEquip:u["a"]},data:function(){return{formInline:{},loading:!1,tableData:[]}},methods:{getList:function(){var e=this;return Object(l["a"])(regeneratorRuntime.mark((function t(){return regeneratorRuntime.wrap((function(t){while(1)switch(t.prev=t.next){case 0:try{e.loading=!0}catch(n){e.loading=!1}case 1:case"end":return t.stop()}}),t)})))()},classChanged:function(e){this.formInline.class=e},selectModel:function(e){console.log(e,555)},selectBatchEquip:function(e){},sendOut:function(e,t){},view:function(e,t){}}},s=c,d=n("2877"),f=Object(d["a"])(s,a,r,!1,null,null,null);t["default"]=f.exports},"64dc":function(e,t,n){"use strict";n.d(t,"l",(function(){return l})),n.d(t,"j",(function(){return o})),n.d(t,"b",(function(){return i})),n.d(t,"h",(function(){return u})),n.d(t,"e",(function(){return c})),n.d(t,"a",(function(){return s})),n.d(t,"i",(function(){return d})),n.d(t,"f",(function(){return f})),n.d(t,"k",(function(){return b})),n.d(t,"c",(function(){return m})),n.d(t,"g",(function(){return h})),n.d(t,"d",(function(){return p}));var a=n("b775"),r=n("99b1");function l(){return Object(a["a"])({url:r["a"].WarehouseNamesUrl,method:"get"})}function o(e){return Object(a["a"])({url:r["a"].WarehouseInfoUrl,method:"get",params:e})}function i(e,t,n){return Object(a["a"])({url:t?r["a"].WarehouseInfoUrl+t+"/":r["a"].WarehouseInfoUrl,method:e,data:n})}function u(e){return Object(a["a"])({url:r["a"].WarehouseInfoUrl+e+"/reversal_use_flag/",method:"put"})}function c(e){return Object(a["a"])({url:r["a"].StationInfoUrl,method:"get",params:e})}function s(e,t,n){return Object(a["a"])({url:t?r["a"].StationInfoUrl+t+"/":r["a"].StationInfoUrl,method:e,data:n})}function d(e){return Object(a["a"])({url:r["a"].StationInfoUrl+e+"/reversal_use_flag/",method:"put"})}function f(){return Object(a["a"])({url:r["a"].StationTypesUrl,methods:"get"})}function b(e){return Object(a["a"])({url:r["a"].WarehouseMaterialTypeUrl,method:"get",params:e})}function m(e,t,n){return Object(a["a"])({url:t?r["a"].WarehouseMaterialTypeUrl+t+"/":r["a"].WarehouseMaterialTypeUrl,method:e,data:n})}function h(e){return Object(a["a"])({url:r["a"].WarehouseMaterialTypeUrl+e+"/reversal_use_flag/",method:"put"})}function p(){return Object(a["a"])({url:r["a"].MaterialTypesUrl,methods:"get"})}},"68de":function(e,t,n){"use strict";var a=function(){var e=this,t=e.$createElement,n=e._self._c||t;return n("el-select",{attrs:{clearable:"",placeholder:"请选择配料设备"},on:{"visible-change":e.visibleChange,change:e.selectChanged},model:{value:e.name,callback:function(t){e.name=t},expression:"name"}},e._l(e.options,(function(e){return n("el-option",{key:e.id,attrs:{label:e.name,value:e.id}})})),1)},r=[],l=(n("7db0"),n("64dc")),o={data:function(){return{name:"",options:[]}},methods:{getList:function(){var e=this;Object(l["l"])().then((function(t){e.options=t}))},visibleChange:function(e){e&&0===this.options.length&&this.getList()},selectChanged:function(e){var t=this.options.find((function(t){return t.id===e}));this.$emit("selectChanged",t)}}},i=o,u=n("2877"),c=Object(u["a"])(i,a,r,!1,null,null,null);t["a"]=c.exports},"7db0":function(e,t,n){"use strict";var a=n("23e7"),r=n("b727").find,l=n("44d2"),o=n("ae40"),i="find",u=!0,c=o(i);i in[]&&Array(1)[i]((function(){u=!1})),a({target:"Array",proto:!0,forced:u||!c},{find:function(e){return r(this,e,arguments.length>1?arguments[1]:void 0)}}),l(i)},daa1:function(e,t,n){"use strict";n.d(t,"e",(function(){return l})),n.d(t,"b",(function(){return o})),n.d(t,"a",(function(){return i})),n.d(t,"f",(function(){return u})),n.d(t,"g",(function(){return c})),n.d(t,"h",(function(){return s})),n.d(t,"i",(function(){return d})),n.d(t,"c",(function(){return f})),n.d(t,"d",(function(){return b}));var a=n("b775"),r=n("99b1");function l(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},n={url:r["a"].MaterialQuantityDemandedUrl,method:e};return Object.assign(n,t),Object(a["a"])(n)}function o(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},n={url:r["a"].ClassArrangelUrl,method:e};return Object.assign(n,t),Object(a["a"])(n)}function i(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},n={url:r["a"].BanburyPlanUrl,method:e};return Object.assign(n,t),Object(a["a"])(n)}function u(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},n={url:r["a"].MaterialRepertoryUrl,method:e};return Object.assign(n,t),Object(a["a"])(n)}function c(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},n={url:r["a"].MaterialTypelUrl,method:e};return Object.assign(n,t),Object(a["a"])(n)}function s(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},n={url:r["a"].RubberRepertoryUrl,method:e};return Object.assign(n,t),Object(a["a"])(n)}function d(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},n={url:r["a"].StageGlobalUrl,method:e};return Object.assign(n,t),Object(a["a"])(n)}function f(e){return Object(a["a"])({url:r["a"].EquipUrl,method:"get",params:e})}function b(){return Object(a["a"])({url:r["a"].GlobalCodesUrl,method:"get",params:{all:1,class_name:"工序"}})}},f9e3:function(e,t,n){"use strict";var a=function(){var e=this,t=e.$createElement,n=e._self._c||t;return n("el-select",{attrs:{clearable:"",placeholder:"请选择生产机型"},on:{"visible-change":e.visibleChange,change:e.selectChanged},model:{value:e.name,callback:function(t){e.name=t},expression:"name"}},e._l(e.options,(function(e){return n("el-option",{key:e.id,attrs:{label:e.name,value:e.id}})})),1)},r=[],l=(n("7db0"),n("64dc")),o={data:function(){return{name:"",options:[]}},methods:{getList:function(){var e=this;Object(l["l"])().then((function(t){e.options=t}))},visibleChange:function(e){e&&0===this.options.length&&this.getList()},selectChanged:function(e){var t=this.options.find((function(t){return t.id===e}));this.$emit("selectChanged",t)}}},i=o,u=n("2877"),c=Object(u["a"])(i,a,r,!1,null,null,null);t["a"]=c.exports}}]);