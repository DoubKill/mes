(window["webpackJsonp"]=window["webpackJsonp"]||[]).push([["chunk-a84884f8"],{"221c":function(e,t,a){"use strict";a.r(t);var r=function(){var e=this,t=e.$createElement,a=e._self._c||t;return a("div",[a("el-form",{attrs:{inline:!0}},[a("el-form-item",{attrs:{label:"日期"}},[a("el-date-picker",{attrs:{type:"date",format:"yyyy-MM-dd","value-format":"yyyy-MM-dd",placeholder:"选择日期"},on:{change:e.changeSearch},model:{value:e.search_time,callback:function(t){e.search_time=t},expression:"search_time"}})],1),a("el-form-item",{attrs:{label:"班次"}},[a("el-select",{staticStyle:{width:"150px"},attrs:{clearable:"",placeholder:"请选择"},on:{"visible-change":e.shifts_class_arrangeChange,change:e.changeSearch},model:{value:e.classes_arrange,callback:function(t){e.classes_arrange=t},expression:"classes_arrange"}},e._l(e.classes_arrangeOptions,(function(e){return a("el-option",{key:e.global_name,attrs:{label:e.global_name,value:e.global_name}})})),1)],1),a("el-form-item",{attrs:{label:"胶料配料编码"}},[a("el-input",{on:{input:e.changeSearch},model:{value:e.rubber_recipe_no,callback:function(t){e.rubber_recipe_no=t},expression:"rubber_recipe_no"}})],1)],1),a("el-table",{staticStyle:{width:"100%"},attrs:{"highlight-current-row":"",data:e.tableData,border:""}},[a("el-table-column",{attrs:{width:"40%",type:"index",label:"No",align:"center"}}),a("el-table-column",{attrs:{width:"60%",prop:"classes",label:"班次",align:"center"}}),a("el-table-column",{attrs:{prop:"product_no",label:"胶料配料编码",align:"center"}}),a("el-table-column",{attrs:{prop:"material_type",label:"原材料类型",align:"center"}}),a("el-table-column",{attrs:{prop:"material_no",label:"原材料编码",align:"center"}}),a("el-table-column",{attrs:{prop:"material_name",label:"原材料名称",align:"center"}}),a("el-table-column",{attrs:{align:"center",label:"原材料库存"}},[a("el-table-column",{attrs:{align:"center",prop:"qty",label:"数量",width:"90px"}}),a("el-table-column",{attrs:{align:"center",prop:"unit_weight",label:"单位重量",width:"80px"}}),a("el-table-column",{attrs:{align:"center",prop:"total_weight",label:"总重量",width:"110px"}})],1),a("el-table-column",{attrs:{align:"center",label:"需求量"}},[a("el-table-column",{attrs:{align:"center",prop:"need_qty",label:"数量",width:"90px"}}),a("el-table-column",{attrs:{align:"center",prop:"need_unit_weight",label:"单位重量",width:"90px"}}),a("el-table-column",{attrs:{align:"center",prop:"material_demanded",label:"总重量",width:"110px"}})],1)],1),a("page",{attrs:{total:e.total,"current-page":e.getParams.page},on:{currentChange:e.currentChange}})],1)},n=[],l=(a("6a61"),a("cf7f")),c=a("3e51"),s=a("daa1"),i={components:{page:c["a"]},data:function(){return{tableData:[],total:0,getParams:{page:1},search_time:null,classes_arrangeOptions:[],rubber_recipe_no:null,classes_arrange:null}},created:function(){this.getSearchTime(),this.material_quantity_list()},methods:{material_quantity_list:function(){var e=this;return Object(l["a"])(regeneratorRuntime.mark((function t(){var a;return regeneratorRuntime.wrap((function(t){while(1)switch(t.prev=t.next){case 0:return t.prev=0,t.next=3,Object(s["e"])("get",{params:e.getParams});case 3:a=t.sent,e.tableData=a.results,e.total=a.count,t.next=11;break;case 8:throw t.prev=8,t.t0=t["catch"](0),new Error(t.t0);case 11:case"end":return t.stop()}}),t,null,[[0,8]])})))()},class_arrange_list:function(){var e=this;return Object(l["a"])(regeneratorRuntime.mark((function t(){var a;return regeneratorRuntime.wrap((function(t){while(1)switch(t.prev=t.next){case 0:return t.prev=0,t.next=3,Object(s["b"])("get",{params:{}});case 3:a=t.sent,0!==a.results.length&&(e.classes_arrangeOptions=a.results),t.next=10;break;case 7:throw t.prev=7,t.t0=t["catch"](0),new Error(t.t0);case 10:case"end":return t.stop()}}),t,null,[[0,7]])})))()},shifts_class_arrangeChange:function(e){e&&this.class_arrange_list()},changeSearch:function(){this.getParams["plan_date"]=this.search_time,this.getParams["classes"]=this.classes_arrange,this.getParams["product_no"]=this.rubber_recipe_no,this.getParams.page=1,this.material_quantity_list()},getSearchTime:function(){var e=new Date,t=e.getFullYear(),a=e.getMonth()+1,r=a<10?"0"+a:a,n=e.getDate(),l=n<10?"0"+n:n;this.search_time=t+"-"+r+"-"+l,this.getParams["plan_date"]=this.search_time},currentChange:function(e){this.getParams.page=e,this.material_quantity_list()}}},o=i,u=a("9ca4"),h=Object(u["a"])(o,r,n,!1,null,"3108c223",null);t["default"]=h.exports},daa1:function(e,t,a){"use strict";a.d(t,"e",(function(){return l})),a.d(t,"b",(function(){return c})),a.d(t,"a",(function(){return s})),a.d(t,"f",(function(){return i})),a.d(t,"g",(function(){return o})),a.d(t,"h",(function(){return u})),a.d(t,"i",(function(){return h})),a.d(t,"c",(function(){return g})),a.d(t,"d",(function(){return b}));var r=a("b775"),n=a("99b1");function l(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},a={url:n["a"].MaterialQuantityDemandedUrl,method:e};return Object.assign(a,t),Object(r["a"])(a)}function c(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},a={url:n["a"].ClassArrangelUrl,method:e};return Object.assign(a,t),Object(r["a"])(a)}function s(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},a={url:n["a"].BanburyPlanUrl,method:e};return Object.assign(a,t),Object(r["a"])(a)}function i(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},a={url:n["a"].MaterialRepertoryUrl,method:e};return Object.assign(a,t),Object(r["a"])(a)}function o(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},a={url:n["a"].MaterialTypelUrl,method:e};return Object.assign(a,t),Object(r["a"])(a)}function u(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},a={url:n["a"].RubberRepertoryUrl,method:e};return Object.assign(a,t),Object(r["a"])(a)}function h(e){var t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},a={url:n["a"].StageGlobalUrl,method:e};return Object.assign(a,t),Object(r["a"])(a)}function g(e){return Object(r["a"])({url:n["a"].EquipUrl,method:"get",params:e})}function b(){return Object(r["a"])({url:n["a"].GlobalCodesUrl,method:"get",params:{all:1,class_name:"工序"}})}}}]);