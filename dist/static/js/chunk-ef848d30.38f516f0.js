(window["webpackJsonp"]=window["webpackJsonp"]||[]).push([["chunk-ef848d30"],{"0516":function(t,e,n){"use strict";n.r(e);var a=function(){var t=this,e=t.$createElement,n=t._self._c||e;return n("div",{staticClass:"app-container"},[n("el-form",{attrs:{inline:!0}},[n("el-form-item",{attrs:{label:"生产日期选择"}},[n("el-date-picker",{attrs:{type:"date","value-format":"yyyy-MM-dd",placeholder:"选择日期"},model:{value:t.search.date,callback:function(e){t.$set(t.search,"date",e)},expression:"search.date"}})],1),n("el-form-item",{attrs:{label:"状态"}},[n("el-select",{attrs:{placeholder:"请选择状态"},model:{value:t.search.a,callback:function(e){t.$set(t.search,"a",e)},expression:"search.a"}},t._l(t.options1,(function(t){return n("el-option",{key:t.value,attrs:{label:t.label,value:t.value}})})),1)],1),n("el-form-item",{attrs:{label:"胶料编码"}},[n("ProductNoSelect",{on:{productBatchingChanged:t.productBatchingChanged}})],1)],1),n("el-table",{staticStyle:{width:"100%"},attrs:{data:t.list,border:"",fit:""}},[n("el-table-column",{attrs:{label:"No",type:"index",align:"center"}}),n("el-table-column",{attrs:{label:"生产日期",align:"center",prop:""}}),n("el-table-column",{attrs:{label:"lot追踪号",align:"center",prop:""}}),n("el-table-column",{attrs:{label:"班次",align:"center",prop:""}}),n("el-table-column",{attrs:{label:"机台",align:"center",prop:""}}),n("el-table-column",{attrs:{label:"胶料编码",align:"center",prop:""}}),n("el-table-column",{attrs:{label:"检测结果",align:"center",prop:""}}),n("el-table-column",{attrs:{label:"等级",align:"center",prop:""}}),n("el-table-column",{attrs:{label:"过期时间",align:"center",prop:""}}),n("el-table-column",{attrs:{label:"超时时间",align:"center",prop:""}}),n("el-table-column",{attrs:{label:"状态",align:"center"},scopedSlots:t._u([{key:"default",fn:function(e){var n=e.row;return[t._v(" "+t._s(t.setOperation(n.state))+" ")]}}])}),n("el-table-column",{attrs:{label:"操作",align:"center"}},[[n("el-button",{on:{click:function(e){t.dialogFormVisible=!0}}},[t._v("处理")]),n("el-button",{on:{click:t.confirmFun}},[t._v("确认")])]],2),n("el-table-column",{attrs:{label:"处理结果",align:"center",prop:""}}),n("el-table-column",{attrs:{label:"处理人",align:"center",prop:""}})],1),n("el-dialog",{attrs:{title:"处理弹框",visible:t.dialogFormVisible},on:{"update:visible":function(e){t.dialogFormVisible=e}}},[n("el-form",[n("el-form-item",{attrs:{label:"处理"}},[n("el-select")],1),n("el-form-item",{attrs:{label:"出库"}},[n("el-checkbox")],1),n("el-form-item",[n("el-button",[t._v("新建处理意见")])],1)],1),n("div",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[n("el-button",{on:{click:function(e){t.dialogFormVisible=!1}}},[t._v(" 取消 ")]),n("el-button",{attrs:{type:"primary"},on:{click:function(e){"create"===t.dialogStatus?t.createData():t.updateData()}}},[t._v(" 确定 ")])],1)],1)],1)},r=[],o=(n("96cf"),n("1da1")),c=n("1c2f"),l={components:{ProductNoSelect:c["a"]},data:function(){return{list:[{}],search:{},options1:[],dialogFormVisible:!1}},methods:{getList:function(){},productBatchingChanged:function(t){},setOperation:function(t){switch(t){case 1:return"待处理";case 2:return"待确定";case 3:return"已确定"}},confirmFun:function(){var t=this;this.$confirm("确认提交?","提示",{confirmButtonText:"确定",cancelButtonText:"取消",type:"warning"}).then(Object(o["a"])(regeneratorRuntime.mark((function e(){return regeneratorRuntime.wrap((function(e){while(1)switch(e.prev=e.next){case 0:t.$message.success("操作成功"),t.getList();case 2:case"end":return e.stop()}}),e)})))).catch((function(){}))}}},i=l,u=n("2877"),s=Object(u["a"])(i,a,r,!1,null,null,null);e["default"]=s.exports},"13d5":function(t,e,n){"use strict";var a=n("23e7"),r=n("d58f").left,o=n("a640"),c=n("ae40"),l=o("reduce"),i=c("reduce",{1:0});a({target:"Array",proto:!0,forced:!l||!i},{reduce:function(t){return r(this,t,arguments.length,arguments.length>1?arguments[1]:void 0)}})},"1c2f":function(t,e,n){"use strict";var a=function(){var t=this,e=t.$createElement,n=t._self._c||e;return n("el-select",{attrs:{clearable:"",filterable:"",loading:t.loading},on:{change:t.productBatchingChanged,"visible-change":t.visibleChange},model:{value:t.productBatchingId,callback:function(e){t.productBatchingId=e},expression:"productBatchingId"}},t._l(t.productBatchings,(function(t){return n("el-option",{key:t.id,attrs:{label:t.stage_product_batch_no,value:t.id}})})),1)},r=[],o=(n("4de4"),n("4160"),n("13d5"),n("159b"),n("1f6c")),c={props:{isStageProductbatchNoRemove:{type:Boolean,default:!1},makeUseBatch:{type:Boolean,default:!1}},data:function(){return{productBatchings:[],productBatchingId:"",productBatchingById:{},loading:!0}},created:function(){},methods:{productBatchingChanged:function(){this.$emit("productBatchingChanged",this.productBatchingById[this.productBatchingId])},visibleChange:function(t){t&&0===this.productBatchings.length&&this.getProductBatchings()},getProductBatchings:function(){var t=this;this.loading=!0,Object(o["G"])("get",null,{params:{all:1}}).then((function(e){var n=e.results;if(n.forEach((function(e){t.productBatchingById[e.id]=e})),t.makeUseBatch){var a=[];a=n.filter((function(t){return 4===t.used_type||6===t.used_type})),n=a}if(t.isStageProductbatchNoRemove){var r={},o=n.reduce((function(t,e){return r[e.stage_product_batch_no]||(r[e.stage_product_batch_no]=t.push(e)),t}),[]);n=o||[]}t.loading=!1,t.productBatchings=n}))}}},l=c,i=n("2877"),u=Object(i["a"])(l,a,r,!1,null,null,null);e["a"]=u.exports},"1f6c":function(t,e,n){"use strict";n.d(e,"k",(function(){return o})),n.d(e,"M",(function(){return c})),n.d(e,"A",(function(){return l})),n.d(e,"z",(function(){return i})),n.d(e,"w",(function(){return u})),n.d(e,"E",(function(){return s})),n.d(e,"e",(function(){return d})),n.d(e,"j",(function(){return b})),n.d(e,"G",(function(){return h})),n.d(e,"m",(function(){return f})),n.d(e,"c",(function(){return g})),n.d(e,"x",(function(){return v})),n.d(e,"L",(function(){return m})),n.d(e,"h",(function(){return p})),n.d(e,"C",(function(){return O})),n.d(e,"B",(function(){return j})),n.d(e,"D",(function(){return y})),n.d(e,"l",(function(){return P})),n.d(e,"I",(function(){return B})),n.d(e,"J",(function(){return U})),n.d(e,"v",(function(){return M})),n.d(e,"q",(function(){return T})),n.d(e,"u",(function(){return C})),n.d(e,"g",(function(){return k})),n.d(e,"K",(function(){return _})),n.d(e,"a",(function(){return I})),n.d(e,"s",(function(){return S})),n.d(e,"p",(function(){return w})),n.d(e,"r",(function(){return F})),n.d(e,"o",(function(){return x})),n.d(e,"b",(function(){return D})),n.d(e,"d",(function(){return L})),n.d(e,"i",(function(){return E})),n.d(e,"f",(function(){return R})),n.d(e,"H",(function(){return N})),n.d(e,"F",(function(){return $})),n.d(e,"t",(function(){return V})),n.d(e,"n",(function(){return q})),n.d(e,"y",(function(){return G}));var a=n("b775"),r=n("99b1");function o(t){var e=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},n={url:r["a"].GlobalCodesUrl,method:t};return Object.assign(n,e),Object(a["a"])(n)}function c(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].WorkSchedulesUrl+e+"/":r["a"].WorkSchedulesUrl,method:t};return Object.assign(o,n),Object(a["a"])(o)}function l(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].PlanSchedulesUrl+e+"/":r["a"].PlanSchedulesUrl,method:t};return Object.assign(o,n),Object(a["a"])(o)}function i(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].PlanScheduleUrl+e+"/":r["a"].PlanScheduleUrl,method:t};return Object.assign(o,n),Object(a["a"])(o)}function u(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].MaterialsUrl+e+"/":r["a"].MaterialsUrl,method:t};return Object.assign(o,n),Object(a["a"])(o)}function s(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].ProductInfosUrl+e+"/":r["a"].ProductInfosUrl,method:t};return Object.assign(o,n),Object(a["a"])(o)}function d(t){var e=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},n={url:r["a"].CopyProductInfosUrl,method:t};return Object.assign(n,e),Object(a["a"])(n)}function b(t){var e=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},n={url:r["a"].EquipUrl,method:t};return Object.assign(n,e),Object(a["a"])(n)}function h(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].RubberMaterialUrl+e+"/":r["a"].RubberMaterialUrl,method:t};return Object.assign(o,n),Object(a["a"])(o)}function f(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].InternalMixerUrl+e+"/":r["a"].InternalMixerUrl,method:t};return Object.assign(o,n),Object(a["a"])(o)}function g(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].ClassesListUrl+e+"/":r["a"].ClassesListUrl,method:t};return Object.assign(o,n),Object(a["a"])(o)}function v(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].PalletFeedBacksUrl+e+"/":r["a"].PalletFeedBacksUrl,method:t};return Object.assign(o,n),Object(a["a"])(o)}function m(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].TrainsFeedbacksUrl+e+"/":r["a"].TrainsFeedbacksUrl,method:t};return Object.assign(o,n),Object(a["a"])(o)}function p(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].EchartsListUrl+e+"/":r["a"].EchartsListUrl,method:t};return Object.assign(o,n),Object(a["a"])(o)}function O(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].ProductClassesPlanUrl+e+"/":r["a"].ProductClassesPlanUrl,method:t};return Object.assign(o,n),Object(a["a"])(o)}function j(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].ProductClassesPlanPanycreateUrl+e+"/":r["a"].ProductClassesPlanPanycreateUrl,method:t};return Object.assign(o,n),Object(a["a"])(o)}function y(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].ProductDayPlanNotice+e+"/":r["a"].ProductDayPlanNotice,method:t};return Object.assign(o,n),Object(a["a"])(o)}function P(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].HomePageUrl+e+"/":r["a"].HomePageUrl,method:t};return Object.assign(o,n),Object(a["a"])(o)}function B(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].TestIndicators+e+"/":r["a"].TestIndicators,method:t};return Object.assign(o,n),Object(a["a"])(o)}function U(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].TestSubTypes+e+"/":r["a"].TestSubTypes,method:t};return Object.assign(o,n),Object(a["a"])(o)}function M(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].MaterialTestOrders+e+"/":r["a"].MaterialTestOrders,method:t};return Object.assign(o,n),Object(a["a"])(o)}function T(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].MatIndicatorTab+e+"/":r["a"].MatIndicatorTab,method:t};return Object.assign(o,n),Object(a["a"])(o)}function C(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].MaterialDataPoints+e+"/":r["a"].MaterialDataPoints,method:t};return Object.assign(o,n),Object(a["a"])(o)}function k(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].DataPoints+e+"/":r["a"].DataPoints,method:t};return Object.assign(o,n),Object(a["a"])(o)}function _(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].TestTypes+e+"/":r["a"].TestTypes,method:t};return Object.assign(o,n),Object(a["a"])(o)}function I(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].BatchingMaterials+e+"/":r["a"].BatchingMaterials,method:t};return Object.assign(o,n),Object(a["a"])(o)}function S(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].MatTestMethods+e+"/":r["a"].MatTestMethods,method:t};return Object.assign(o,n),Object(a["a"])(o)}function w(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].MatDataPointIndicators+e+"/":r["a"].MatDataPointIndicators,method:t};return Object.assign(o,n),Object(a["a"])(o)}function F(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].MatTestIndicatorMethods+e+"/":r["a"].MatTestIndicatorMethods,method:t};return Object.assign(o,n),Object(a["a"])(o)}function x(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].LevelResult+e+"/":r["a"].LevelResult,method:t};return Object.assign(o,n),Object(a["a"])(o)}function D(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].ClassesBanburySummary+e+"/":r["a"].ClassesBanburySummary,method:t};return Object.assign(o,n),Object(a["a"])(o)}function L(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].CollectTrainsFeed+e+"/":r["a"].CollectTrainsFeed,method:t};return Object.assign(o,n),Object(a["a"])(o)}function E(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].EquipBanburySummary+e+"/":r["a"].EquipBanburySummary,method:t};return Object.assign(o,n),Object(a["a"])(o)}function R(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].CutTimeCollect+e+"/":r["a"].CutTimeCollect,method:t};return Object.assign(o,n),Object(a["a"])(o)}function N(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].SumSollectTrains+e+"/":r["a"].SumSollectTrains,method:t};return Object.assign(o,n),Object(a["a"])(o)}function $(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].PutPlanManagement+e+"/":r["a"].PutPlanManagement,method:t};return Object.assign(o,n),Object(a["a"])(o)}function V(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].MaterialCount+e+"/":r["a"].MaterialCount,method:t};return Object.assign(o,n),Object(a["a"])(o)}function q(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].InventoryLog+e+"/":r["a"].InventoryLog,method:t};return Object.assign(o,n),Object(a["a"])(o)}function G(t,e){var n=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o={url:e?r["a"].PalletTrainsFeedbacks+e+"/":r["a"].PalletTrainsFeedbacks,method:t};return Object.assign(o,n),Object(a["a"])(o)}},d58f:function(t,e,n){var a=n("1c0b"),r=n("7b0b"),o=n("44ad"),c=n("50c4"),l=function(t){return function(e,n,l,i){a(n);var u=r(e),s=o(u),d=c(u.length),b=t?d-1:0,h=t?-1:1;if(l<2)while(1){if(b in s){i=s[b],b+=h;break}if(b+=h,t?b<0:d<=b)throw TypeError("Reduce of empty array with no initial value")}for(;t?b>=0:d>b;b+=h)b in s&&(i=n(i,s[b],b,u));return i}};t.exports={left:l(!1),right:l(!0)}}}]);