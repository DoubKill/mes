(window["webpackJsonp"]=window["webpackJsonp"]||[]).push([["chunk-2acba386"],{"1b10":function(t,e,a){"use strict";var n=function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",{staticClass:"card-container"},[a("table",{staticClass:"info-table",attrs:{border:"1",bordercolor:"black"}},[a("tbody",[t._m(0),a("tr",[a("td",{attrs:{colspan:"4"}},[t._v(t._s(t.testData.product_no))]),t._m(1)]),a("tr",[a("td",[t._v("工厂日期")]),a("td",[t._v(t._s(t.testData.day_time))]),a("td",[t._v("生产班次")]),a("td",[t._v(t._s(t.testData.classes_group))])]),a("tr",[a("td",[t._v("生产机台")]),a("td",[t._v(t._s(t.testData.equip_no))]),a("td",[t._v("生产车次")]),a("td",[t._v(t._s(t.testData.actual_trains))])]),a("tr",[a("td",[t._v("收皮重量")]),a("td",[t._v(t._s(t.testData.actual_weight))]),a("td",[t._v("余量")]),a("td",[t._v(t._s(t.testData.residual_weight))])]),a("tr",[a("td",[t._v("生产时间")]),a("td",{attrs:{colspan:"3"}},[t._v(t._s(t.testData.production_factory_date))])]),a("tr",[a("td",[t._v("有效时间")]),a("td",{attrs:{colspan:"3"}},[t._v(t._s(t.testData.valid_time))])]),a("tr",[a("td",[t._v("收皮员")]),a("td",[t._v(t._s(t.testData.operation_user))]),a("td",[t._v("备注")]),a("td")]),t._m(2),a("tr",[a("td",[t._v("检测时间")]),a("td",{attrs:{colspan:"3"}},[t._v(t._s(t.testData.test?t.testData.test.test_factory_date:""))])]),a("tr",[a("td",[t._v("打印时间")]),a("td",{attrs:{colspan:"3"}},[t._v(t._s(t.testData.print_time))])]),a("tr",[a("td",[t._v("检测员")]),a("td",[t._v(t._s(t.testData.test?t.testData.test.test_user:""))]),a("td",[t._v("检测班次")]),a("td",[t._v(t._s(t.testData.test?t.testData.test.test_class:""))])]),a("tr",[a("td",[t._v("检测结果")]),a("td",[t._v(t._s(t.testData.deal_result))]),a("td",[t._v("备注")]),a("td",[t._v(t._s(t.testData.test?t.testData.test.test_note:""))])]),a("tr",[a("td",[t._v("处理人")]),a("td",[t._v(t._s(t.testData.deal_user))]),a("td",[t._v("处理时间")]),a("td",[t._v(t._s(t.testData.deal_time))])]),a("tr",[a("td",[t._v("处理意见")]),a("td",{attrs:{colspan:"3"}},[t._v(t._s(t.testData.deal_suggestion))])])])]),a("table",{attrs:{border:"2",bordercolor:"black"}},[a("tr",[a("th",{staticStyle:{width:"100px"},attrs:{rowspan:"2"}},[t._v("车次")]),t._l(t.testData.mtr_list.table_head,(function(e,n){return a("th",{key:n,staticStyle:{"min-width":"80px","max-width":"80px"},attrs:{colspan:e.length}},[t._v(t._s(n))])})),a("th",{staticStyle:{width:"100px"},attrs:{rowspan:"2"}},[t._v("综合判级")])],2),a("tr",t._l(t.testData.mtr_list.sub_head,(function(e,n){return a("th",{key:n},[t._v(t._s(e))])})),0),t._l(t.testData.mtr_list.rows,(function(e){return a("tr",{key:e},[a("td",[t._v(t._s(e))]),t._l(t.testData.mtr_list[e],(function(n,r){return a("td",{key:r},[t._v(" "+t._s(r!==t.testData.mtr_list[e].length-1?n.value:"")+" "),a("br"),t._v(" "+t._s(n?n.status:"")+" ")])}))],2)}))],2),a("img",{staticClass:"barcode"})])},r=[function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("tr",[a("td",{attrs:{colspan:"5"}},[t._v("胶料信息卡")])])},function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("td",{staticStyle:{transform:"rotate(-90deg)",width:"150px","max-width":"150px"},attrs:{rowspan:"14"}},[a("img",{staticClass:"barcode",staticStyle:{"margin-left":"-120px"}})])},function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("tr",[a("td",{attrs:{colspan:"4"}},[t._v("质量信息卡")])])}],u=(a("99af"),a("7db0"),a("4160"),a("159b"),a("62c5")),s=a.n(u),i={data:function(){return{testData:{test:{},mtr_list:{table_head:[],sub_head:[],rows:[]}}}},methods:{setTestData:function(t){var e=this;this.testData=t,s()(".barcode",this.testData.lot_no,{displayValue:!0}),this.testData.mtr_list.rows=[];var a=function(t){"table_head"!==t&&"rows"!==t&&"sub_head"!==t&&function(){e.testData.mtr_list.rows.push(t);var a=[],n=function(n){e.testData.mtr_list.table_head[n].forEach((function(r){var u=e.testData.mtr_list[t].find((function(t){return t.test_indicator_name===n&&t.data_point_name===r}));a.push(u||{})}))};for(var r in e.testData.mtr_list.table_head)n(r);for(var u=0,s=null,i=0;i<a.length;i++)a[i].max_test_times>u&&(u=a[i].max_test_times,s=a[i]);s&&a.push(s),e.testData.mtr_list[t]=a}()};for(var n in this.testData.mtr_list)a(n);for(var r in this.testData.mtr_list.sub_head=[],this.testData.mtr_list.table_head)this.testData.mtr_list.sub_head=this.testData.mtr_list.sub_head.concat(this.testData.mtr_list.table_head[r])}}},c=i,l=(a("a56a"),a("2877")),o=Object(l["a"])(c,n,r,!1,null,null,null);e["a"]=o.exports},"1f6c":function(t,e,a){"use strict";a.d(e,"k",(function(){return u})),a.d(e,"L",(function(){return s})),a.d(e,"z",(function(){return i})),a.d(e,"y",(function(){return c})),a.d(e,"w",(function(){return l})),a.d(e,"D",(function(){return o})),a.d(e,"e",(function(){return d})),a.d(e,"j",(function(){return h})),a.d(e,"F",(function(){return b})),a.d(e,"m",(function(){return f})),a.d(e,"c",(function(){return v})),a.d(e,"x",(function(){return _})),a.d(e,"K",(function(){return m})),a.d(e,"h",(function(){return g})),a.d(e,"B",(function(){return O})),a.d(e,"A",(function(){return j})),a.d(e,"C",(function(){return p})),a.d(e,"l",(function(){return D})),a.d(e,"H",(function(){return y})),a.d(e,"I",(function(){return U})),a.d(e,"v",(function(){return P})),a.d(e,"q",(function(){return S})),a.d(e,"u",(function(){return T})),a.d(e,"g",(function(){return M})),a.d(e,"J",(function(){return C})),a.d(e,"a",(function(){return w})),a.d(e,"s",(function(){return k})),a.d(e,"p",(function(){return I})),a.d(e,"r",(function(){return x})),a.d(e,"o",(function(){return q})),a.d(e,"b",(function(){return E})),a.d(e,"d",(function(){return B})),a.d(e,"i",(function(){return F})),a.d(e,"f",(function(){return L})),a.d(e,"G",(function(){return R})),a.d(e,"E",(function(){return $})),a.d(e,"t",(function(){return A})),a.d(e,"n",(function(){return G}));var n=a("b775"),r=a("99b1");function u(t){var e=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},a={url:r["a"].GlobalCodesUrl,method:t};return Object.assign(a,e),Object(n["a"])(a)}function s(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].WorkSchedulesUrl+e+"/":r["a"].WorkSchedulesUrl,method:t};return Object.assign(u,a),Object(n["a"])(u)}function i(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].PlanSchedulesUrl+e+"/":r["a"].PlanSchedulesUrl,method:t};return Object.assign(u,a),Object(n["a"])(u)}function c(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].PlanScheduleUrl+e+"/":r["a"].PlanScheduleUrl,method:t};return Object.assign(u,a),Object(n["a"])(u)}function l(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].MaterialsUrl+e+"/":r["a"].MaterialsUrl,method:t};return Object.assign(u,a),Object(n["a"])(u)}function o(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].ProductInfosUrl+e+"/":r["a"].ProductInfosUrl,method:t};return Object.assign(u,a),Object(n["a"])(u)}function d(t){var e=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},a={url:r["a"].CopyProductInfosUrl,method:t};return Object.assign(a,e),Object(n["a"])(a)}function h(t){var e=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},a={url:r["a"].EquipUrl,method:t};return Object.assign(a,e),Object(n["a"])(a)}function b(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].RubberMaterialUrl+e+"/":r["a"].RubberMaterialUrl,method:t};return Object.assign(u,a),Object(n["a"])(u)}function f(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].InternalMixerUrl+e+"/":r["a"].InternalMixerUrl,method:t};return Object.assign(u,a),Object(n["a"])(u)}function v(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].ClassesListUrl+e+"/":r["a"].ClassesListUrl,method:t};return Object.assign(u,a),Object(n["a"])(u)}function _(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].PalletFeedBacksUrl+e+"/":r["a"].PalletFeedBacksUrl,method:t};return Object.assign(u,a),Object(n["a"])(u)}function m(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].TrainsFeedbacksUrl+e+"/":r["a"].TrainsFeedbacksUrl,method:t};return Object.assign(u,a),Object(n["a"])(u)}function g(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].EchartsListUrl+e+"/":r["a"].EchartsListUrl,method:t};return Object.assign(u,a),Object(n["a"])(u)}function O(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].ProductClassesPlanUrl+e+"/":r["a"].ProductClassesPlanUrl,method:t};return Object.assign(u,a),Object(n["a"])(u)}function j(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].ProductClassesPlanPanycreateUrl+e+"/":r["a"].ProductClassesPlanPanycreateUrl,method:t};return Object.assign(u,a),Object(n["a"])(u)}function p(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].ProductDayPlanNotice+e+"/":r["a"].ProductDayPlanNotice,method:t};return Object.assign(u,a),Object(n["a"])(u)}function D(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].HomePageUrl+e+"/":r["a"].HomePageUrl,method:t};return Object.assign(u,a),Object(n["a"])(u)}function y(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].TestIndicators+e+"/":r["a"].TestIndicators,method:t};return Object.assign(u,a),Object(n["a"])(u)}function U(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].TestSubTypes+e+"/":r["a"].TestSubTypes,method:t};return Object.assign(u,a),Object(n["a"])(u)}function P(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].MaterialTestOrders+e+"/":r["a"].MaterialTestOrders,method:t};return Object.assign(u,a),Object(n["a"])(u)}function S(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].MatIndicatorTab+e+"/":r["a"].MatIndicatorTab,method:t};return Object.assign(u,a),Object(n["a"])(u)}function T(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].MaterialDataPoints+e+"/":r["a"].MaterialDataPoints,method:t};return Object.assign(u,a),Object(n["a"])(u)}function M(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].DataPoints+e+"/":r["a"].DataPoints,method:t};return Object.assign(u,a),Object(n["a"])(u)}function C(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].TestTypes+e+"/":r["a"].TestTypes,method:t};return Object.assign(u,a),Object(n["a"])(u)}function w(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].BatchingMaterials+e+"/":r["a"].BatchingMaterials,method:t};return Object.assign(u,a),Object(n["a"])(u)}function k(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].MatTestMethods+e+"/":r["a"].MatTestMethods,method:t};return Object.assign(u,a),Object(n["a"])(u)}function I(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].MatDataPointIndicators+e+"/":r["a"].MatDataPointIndicators,method:t};return Object.assign(u,a),Object(n["a"])(u)}function x(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].MatTestIndicatorMethods+e+"/":r["a"].MatTestIndicatorMethods,method:t};return Object.assign(u,a),Object(n["a"])(u)}function q(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].LevelResult+e+"/":r["a"].LevelResult,method:t};return Object.assign(u,a),Object(n["a"])(u)}function E(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].ClassesBanburySummary+e+"/":r["a"].ClassesBanburySummary,method:t};return Object.assign(u,a),Object(n["a"])(u)}function B(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].CollectTrainsFeed+e+"/":r["a"].CollectTrainsFeed,method:t};return Object.assign(u,a),Object(n["a"])(u)}function F(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].EquipBanburySummary+e+"/":r["a"].EquipBanburySummary,method:t};return Object.assign(u,a),Object(n["a"])(u)}function L(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].CutTimeCollect+e+"/":r["a"].CutTimeCollect,method:t};return Object.assign(u,a),Object(n["a"])(u)}function R(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].SumSollectTrains+e+"/":r["a"].SumSollectTrains,method:t};return Object.assign(u,a),Object(n["a"])(u)}function $(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].PutPlanManagement+e+"/":r["a"].PutPlanManagement,method:t};return Object.assign(u,a),Object(n["a"])(u)}function A(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].MaterialCount+e+"/":r["a"].MaterialCount,method:t};return Object.assign(u,a),Object(n["a"])(u)}function G(t,e){var a=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},u={url:e?r["a"].InventoryLog+e+"/":r["a"].InventoryLog,method:t};return Object.assign(u,a),Object(n["a"])(u)}},"34be":function(t,e,a){"use strict";var n=function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("el-select",{attrs:{clearable:"",filterable:"",placeholder:"倒班规则"},on:{change:t.selectChanged},model:{value:t.planScheduleId,callback:function(e){t.planScheduleId=e},expression:"planScheduleId"}},t._l(t.planSchedules,(function(t){return a("el-option",{key:t.id,attrs:{label:t.work_schedule__schedule_name,value:t.id}})})),1)},r=[],u=(a("96cf"),a("1da1")),s=a("1f6c"),i={props:{dayTime:{type:String}},data:function(){return{planScheduleId:null,planSchedules:[]}},watch:{dayTime:function(t){this.planScheduleId=null,this.getPlanSchedules()}},created:function(){this.getPlanSchedules()},methods:{getPlanSchedules:function(){var t=this;return Object(u["a"])(regeneratorRuntime.mark((function e(){var a;return regeneratorRuntime.wrap((function(e){while(1)switch(e.prev=e.next){case 0:if(t.planSchedules=[],!t.dayTime){e.next=11;break}return e.prev=2,e.next=5,Object(s["y"])("get",null,{params:{all:1,day_time:t.dayTime}});case 5:a=e.sent,t.planSchedules=a.results,e.next=11;break;case 9:e.prev=9,e.t0=e["catch"](2);case 11:case"end":return e.stop()}}),e,null,[[2,9]])})))()},selectChanged:function(){this.$emit("planScheduleSelected",this.planScheduleId)}}},c=i,l=a("2877"),o=Object(l["a"])(c,n,r,!1,null,null,null);e["a"]=o.exports},"66ad":function(t,e,a){"use strict";a.d(e,"b",(function(){return u})),a.d(e,"c",(function(){return s})),a.d(e,"f",(function(){return i})),a.d(e,"a",(function(){return c})),a.d(e,"e",(function(){return l})),a.d(e,"d",(function(){return o})),a.d(e,"g",(function(){return d}));var n=a("b775"),r=a("99b1");function u(t){return Object(n["a"])({url:r["a"].EquipUrl,method:"get",params:t})}function s(t){return Object(n["a"])({url:r["a"].PalletFeedBacksUrl,method:"get",params:t})}function i(t){return Object(n["a"])({url:r["a"].TrainsFeedbacksUrl,method:"get",params:t})}function c(t){return Object(n["a"])({url:r["a"].EchartsListUrl,method:"get",params:t})}function l(t){return Object(n["a"])({url:r["a"].ProductActualUrl,method:"get",params:t})}function o(t){return Object(n["a"])({url:r["a"].PalletFeedbacksUrl,method:"get",params:t})}function d(t){return Object(n["a"])({url:r["a"].ProductDayPlanNoticeUrl,method:"post",id:t})}},"6d0e":function(t,e,a){},8448:function(t,e,a){"use strict";var n=function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("el-select",{attrs:{clearable:"",placeholder:"请选择"},on:{change:t.equipChanged,"visible-change":t.visibleChange},model:{value:t.equipId,callback:function(e){t.equipId=e},expression:"equipId"}},t._l(t.equipOptions,(function(t){return a("el-option",{key:t.id,attrs:{label:t.equip_no,value:t.id}})})),1)},r=[],u=(a("7db0"),a("66ad")),s={data:function(){return{equipId:null,equipOptions:[]}},methods:{visibleChange:function(t){var e=this;t&&Object(u["b"])({all:1}).then((function(t){e.equipOptions=t.results}))},equipChanged:function(){var t=this;this.$emit("equipSelected",this.equipOptions.find((function(e){return e.id===t.equipId})))}}},i=s,c=a("2877"),l=Object(c["a"])(i,n,r,!1,null,null,null);e["a"]=l.exports},"89c6":function(t,e,a){"use strict";a.d(e,"d",(function(){return u})),a.d(e,"b",(function(){return s})),a.d(e,"c",(function(){return i})),a.d(e,"a",(function(){return c}));var n=a("b775"),r=a("99b1");function u(){return Object(n["a"])({url:r["a"].TestTypeDataUrl,method:"get"})}function s(t){return Object(n["a"])({url:r["a"].MaterialTestOrdersUrl,method:"get",params:t})}function i(t){return Object(n["a"])({url:r["a"].PalletFeedTestUrl,method:"get",params:t})}function c(t,e){return Object(n["a"])({url:r["a"].MaterialValidTimeUrl,method:"post",data:{id:t,valid_time:e}})}},a56a:function(t,e,a){"use strict";var n=a("6d0e"),r=a.n(n);r.a},daa1:function(t,e,a){"use strict";a.d(e,"d",(function(){return u})),a.d(e,"b",(function(){return s})),a.d(e,"a",(function(){return i})),a.d(e,"e",(function(){return c})),a.d(e,"f",(function(){return l})),a.d(e,"g",(function(){return o})),a.d(e,"h",(function(){return d})),a.d(e,"c",(function(){return h}));var n=a("b775"),r=a("99b1");function u(t){var e=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},a={url:r["a"].MaterialQuantityDemandedUrl,method:t};return Object.assign(a,e),Object(n["a"])(a)}function s(t){var e=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},a={url:r["a"].ClassArrangelUrl,method:t};return Object.assign(a,e),Object(n["a"])(a)}function i(t){var e=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},a={url:r["a"].BanburyPlanUrl,method:t};return Object.assign(a,e),Object(n["a"])(a)}function c(t){var e=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},a={url:r["a"].MaterialRepertoryUrl,method:t};return Object.assign(a,e),Object(n["a"])(a)}function l(t){var e=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},a={url:r["a"].MaterialTypelUrl,method:t};return Object.assign(a,e),Object(n["a"])(a)}function o(t){var e=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},a={url:r["a"].RubberRepertoryUrl,method:t};return Object.assign(a,e),Object(n["a"])(a)}function d(t){var e=arguments.length>1&&void 0!==arguments[1]?arguments[1]:{},a={url:r["a"].StageGlobalUrl,method:t};return Object.assign(a,e),Object(n["a"])(a)}function h(t){return Object(n["a"])({url:r["a"].EquipUrl,method:"get",params:t})}}}]);