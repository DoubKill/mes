(window["webpackJsonp"]=window["webpackJsonp"]||[]).push([["chunk-46000873"],{1:function(e,t){},2:function(e,t){},3:function(e,t){},"4b5b":function(e,t,a){"use strict";a.r(t);var l=function(){var e=this,t=e.$createElement,a=e._self._c||t;return a("div",{staticClass:"app-container details_style"},[a("el-form",{attrs:{inline:!0}},[a("el-form-item",{attrs:{label:"日期"}},[a("el-date-picker",{attrs:{clearable:!1,type:"date","value-format":"yyyy-MM-dd",placeholder:"选择日期"},on:{change:e.dayTimeChanged},model:{value:e.getParams.day_time,callback:function(t){e.$set(e.getParams,"day_time",t)},expression:"getParams.day_time"}})],1),a("el-form-item",{attrs:{label:"机台"}},[a("equip-select",{attrs:{equip_no_props:e.getParams.equip_no},on:{"update:equip_no_props":function(t){return e.$set(e.getParams,"equip_no",t)},changeSearch:e.equipSelected}})],1),a("el-form-item",{attrs:{label:"胶料"}},[a("all-product-no-select",{on:{productBatchingChanged:e.productBatchingChanged}})],1),a("el-form-item",{attrs:{label:"班次"}},[a("class-select",{on:{classSelected:e.classSelected}})],1),a("el-form-item",{attrs:{label:"段次"}},[a("stage-select",{on:{change:e.stageChange},model:{value:e.getParams.stage,callback:function(t){e.$set(e.getParams,"stage",t)},expression:"getParams.stage"}})],1),a("el-form-item",{attrs:{label:"综合检测结果"}},[a("el-select",{attrs:{placeholder:"请选择",clearable:""},on:{change:e.valueResultFun},model:{value:e.getParams.mes_result,callback:function(t){e.$set(e.getParams,"mes_result",t)},expression:"getParams.mes_result"}},e._l(e.options,(function(e){return a("el-option",{key:e,attrs:{label:e,value:e}})})),1)],1),a("el-form-item",[a("el-button",{attrs:{type:"primary"},on:{click:e.clickQuery}},[e._v("查询")])],1),a("br"),a("el-form-item",[a("el-button",{on:{click:function(t){e.filterDialogVisible=!0}}},[e._v(" 显示过滤界面 ")])],1),a("el-form-item",[a("el-button",{directives:[{name:"permission",rawName:"v-permission",value:["result_info","export"],expression:"['result_info','export']"}],on:{click:e.exportExcel}},[e._v(" 导出 ")])],1)],1),a("el-table",{directives:[{name:"loading",rawName:"v-loading",value:e.listLoading,expression:"listLoading"}],attrs:{id:"out-table",data:e.testOrders,border:"",fit:"","row-key":"index",lazy:"",load:e.load,"max-height":"600",size:"mini","tree-props":{children:"children",hasChildren:"hasChildren"},"row-class-name":e.tableRowClassName}},[a("el-table-column",{attrs:{label:"生产信息",align:"center"}},[a("el-table-column",{attrs:{label:"生产时间",width:"90px",prop:"production_factory_date",align:"center"},scopedSlots:e._u([{key:"default",fn:function(t){var a=t.row;return[e._v(" "+e._s(a.production_factory_date.split(" ")[0])+" ")]}}])}),a("el-table-column",{attrs:{label:"生产班次/班组",prop:"class_group","show-overflow-tooltip":"",width:"75px"}}),a("el-table-column",{attrs:{label:"生产机台",width:"40px",prop:"production_equip_no"}}),a("el-table-column",{attrs:{label:"胶料编码",width:"105px",align:"center",prop:"product_no"}}),a("el-table-column",{attrs:{label:"车次",align:"center",width:"35px",prop:"actual_trains"}}),a("el-table-column",{attrs:{label:"检测状态",width:"35px",prop:"test_status",align:"center"},scopedSlots:e._u([{key:"default",fn:function(t){var l=t.row;return[a("div",{class:"复检"===l.test_status?"test_type_name_style":""},[e._v(" "+e._s(l.test_status)+" ")])]}}])})],1),e._l(e.testTypeList.filter((function(e){return e.show})),(function(t){return a("el-table-column",{key:t.test_type_name,attrs:{align:"center",label:t.test_type_name}},[e._l(t.data_indicator_detail.filter((function(e){return e.show})),(function(l){return a("el-table-column",{key:t.test_type_name+l.detail,attrs:{width:"55px",label:l.detail,align:"center"},scopedSlots:e._u([{key:"default",fn:function(n){var r=n.row;return[a("div",{class:1!==e.getDataPoint(t.test_type_name,l.detail,r.order_results,"level")&&""!==e.getDataPoint(t.test_type_name,l.detail,r.order_results,"level")?"test_type_name_style":""},[e._v(" "+e._s(e.getDataPoint(t.test_type_name,l.detail,r.order_results,"value"))+" ")])]}}],null,!0)})})),"门尼"===t.test_type_name||"流变"===t.test_type_name?a("el-table-column",{attrs:{label:"检测机台",width:"50px",align:"center"},scopedSlots:e._u([{key:"default",fn:function(a){var l=a.row;return[e._v(" "+e._s(e.getDataPoint(t.test_type_name,"maxLevelItem",l.order_results,"machine_name"))+" ")]}}],null,!0)}):e._e(),a("el-table-column",{attrs:{width:"35px",label:"等级",align:"center"},scopedSlots:e._u([{key:"default",fn:function(a){var l=a.row;return[e._v(" "+e._s(e.getDataPoint(t.test_type_name,"maxLevelItem",l.order_results,"level"))+" ")]}}],null,!0)})],2)})),a("el-table-column",{attrs:{label:"综合等级",width:"35px",prop:"level",align:"center"}}),a("el-table-column",{attrs:{label:"综合检测结果","show-overflow-tooltip":"","min-width":"60px",prop:"mes_result",align:"center"}})],2),a("el-dialog",{attrs:{title:"选择过滤",visible:e.filterDialogVisible},on:{"update:visible":function(t){e.filterDialogVisible=t}}},[a("el-table",{attrs:{border:"",data:e.testTypeList}},[a("el-table-column",{attrs:{label:"选择",width:"50"},scopedSlots:e._u([{key:"default",fn:function(t){var l=t.row;return[a("el-checkbox",{model:{value:l.show,callback:function(t){e.$set(l,"show",t)},expression:"row.show"}})]}}])}),a("el-table-column",{attrs:{label:"实验方法",width:"80"},scopedSlots:e._u([{key:"default",fn:function(t){var l=t.row;return[a("span",[e._v(e._s(l.test_type_name))])]}}])}),a("el-table-column",{attrs:{label:"检测项"},scopedSlots:e._u([{key:"default",fn:function(t){var l=t.row;return[e._l(l.data_indicator_detail,(function(t){return[a("el-checkbox",{key:t.detail,model:{value:t.show,callback:function(a){e.$set(t,"show",a)},expression:"item.show"}},[e._v(e._s(t.detail))])]}))]}}])})],1),a("div",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[a("el-button",{on:{click:function(t){e.filterDialogVisible=!1}}},[e._v("关闭")])],1)],1),a("el-dialog",{attrs:{title:"胶料信息卡",width:"80%",visible:e.testCardDialogVisible},on:{"update:visible":function(t){e.testCardDialogVisible=t}}},[a("test-card",{ref:"testCard"})],1)],1)},n=[],r=(a("99af"),a("4de4"),a("4160"),a("d81d"),a("a9e3"),a("159b"),a("5530")),s=(a("96cf"),a("1da1")),i=a("5a0c"),o=a.n(i),c=a("4090"),u=a("cfc4"),d=function(){var e=this,t=e.$createElement,a=e._self._c||t;return a("el-select",{attrs:{value:e.id,clearable:"",placeholder:"请选择"},on:{change:function(t){return e.$emit("change",t)},"visible-change":e.visibleChange}},e._l(e.stageOptions,(function(e){return a("el-option",{key:e.id,attrs:{label:e.global_name,value:e.global_name}})})),1)},p=[],m=a("daa1"),f={model:{prop:"id",event:"change"},props:{id:{type:[Number,String],required:!1,default:void 0}},data:function(){return{stageOptions:[]}},created:function(){this.getStageOptions()},methods:{getStageOptions:function(){var e=this;return Object(s["a"])(regeneratorRuntime.mark((function t(){var a;return regeneratorRuntime.wrap((function(t){while(1)switch(t.prev=t.next){case 0:return t.next=2,Object(m["h"])("get");case 2:a=t.sent,e.stageOptions=a.results;case 4:case"end":return t.stop()}}),t)})))()},visibleChange:function(e){e&&this.getStageOptions()}}},_=f,g=a("2877"),h=Object(g["a"])(_,d,p,!1,null,null,null),b=h.exports,v=a("5dce"),w=a("89c6"),y=a("c21d"),x=a("ecc0"),k=a.n(x),O=a("d85b"),P=a.n(O),S={directives:{"el-table-infinite-scroll":y["a"]},components:{EquipSelect:c["a"],allProductNoSelect:v["a"],ClassSelect:u["a"],StageSelect:b},data:function(){return{count:0,allPage:0,getParams:{day_time:o()().format("YYYY-MM-DD"),equip_no:null,classes:null,product_no:null,stage:null,page:1},listLoading:!0,filterDialogVisible:!1,testCardDialogVisible:!1,testTypeList:[{test_type_id:null,test_type_name:"",show:!1,data_indicator_detail:[{detail:"",show:!1}]}],testOrders:[],testOrdersAll:[],index:1,recordList:[],isMoreLoad:!0,definePafeSize:10,valueResult:"",options:["一等品","三等品"]}},created:function(){this.getTestTypes()},mounted:function(){},beforeUpdata:function(){},methods:{dayTimeChanged:function(){},clearList:function(){this.getParams.page=1,this.allPage=0,this.testOrders=[],this.testOrdersAll=[]},titleInfo:function(e,t){if(!e&&0!==e)throw this.$message.info(t),new Error(t)},equipSelected:function(e){},stageChange:function(){},classSelected:function(e){this.getParams.classes=e||null},productBatchingChanged:function(e){this.getParams.product_no=e?e.material_no:null},load:function(e,t,a){var l=this,n=[];Object(w["d"])(e.id).then((function(t){for(var r in t){var s=JSON.parse(JSON.stringify(e));for(var i in s.index=l.index++,s.hasChildren=!1,s.order_results=t[r],s.level=0,s.mes_result="未检测",s.order_results){var o=s.order_results[i],c=0;for(var u in o){var d=o[u];d.test_times>1&&(s.test_status="复检"),d.level>c&&(c=d.level,o["maxLevelItem"]=d)}c>s.level&&(s.level=c,s.mes_result=1===s.level?"一等品":"三等品")}n.push(s)}a(n)}))},valueResultFun:function(e){},clickQuery:function(){this.getMaterialTestOrders()},getMaterialTestOrders:function(){var e=this;return Object(s["a"])(regeneratorRuntime.mark((function t(){var a,l,n;return regeneratorRuntime.wrap((function(t){while(1)switch(t.prev=t.next){case 0:return e.listLoading=!0,t.prev=1,t.next=4,Object(w["b"])(e.getParams);case 4:a=t.sent,l=a,l=l.map((function(t){return Object(r["a"])(Object(r["a"])({},t),{},{index:e.index++,hasChildren:!1,test_status:"正常",class_group:"".concat(t.production_class,"/").concat(t.production_group)})})),l.forEach((function(e){for(var t in e.level=0,e.mes_result="未检测",e.order_results){var a=e.order_results[t],l=0;for(var n in a){var r=a[n];r.test_times>1&&(e.test_status="复检",e.hasChildren=!0),r.level>l&&(l=r.level,a["maxLevelItem"]=r)}l>e.level&&(e.level=l,e.mes_result=1===e.level?"一等品":"三等品")}})),e.testOrders=l,e.testOrdersAll=l,e.listLoading=!1,e.getParams.mes_result&&(n=[],n=e.testOrdersAll.filter((function(t){return t.mes_result===e.getParams.mes_result})),e.testOrders=n),t.next=17;break;case 14:t.prev=14,t.t0=t["catch"](1),e.listLoading=!1;case 17:case"end":return t.stop()}}),t,null,[[1,14]])})))()},infiniteScroll:function(){Number(this.allPage-this.getParams.page*this.definePafeSize)<0||(this.getParams.page=this.getParams.page+1,this.getMaterialTestOrders())},getTestTypes:function(){var e=this;return Object(s["a"])(regeneratorRuntime.mark((function t(){var a;return regeneratorRuntime.wrap((function(t){while(1)switch(t.prev=t.next){case 0:return t.prev=0,e.testTypeList=[],t.next=4,Object(w["e"])();case 4:a=t.sent,e.testTypeList=a.map((function(e){return e.data_indicator_detail=e.data_indicator_detail.map((function(e){return{detail:e,show:!0}})),Object(r["a"])(Object(r["a"])({},e),{},{show:!0})})),e.listLoading=!1,t.next=12;break;case 9:t.prev=9,t.t0=t["catch"](0),e.listLoading=!1;case 12:case"end":return t.stop()}}),t,null,[[0,9]])})))()},showCard:function(e){var t=this;this.testCardDialogVisible=!0,this.$nextTick((function(){t.$refs["testCard"].setTestData(e)}))},getDataPoint:function(e,t,a,l){var n=a[e]&&a[e][t]?a[e][t]:null;return n?n[l]:""},tableRowClassName:function(e){var t=e.row;e.rowIndex;return"一等品"!==t.mes_result?"warning-row":""},exportExcel:function(){var e=P.a.utils.table_to_book(document.querySelector("#out-table")),t=P.a.write(e,{bookType:"xlsx",bookSST:!0,type:"array"});try{k.a.saveAs(new Blob([t],{type:"application/octet-stream"}),"胶料快检详细信息.xlsx")}catch(a){"undefined"!==typeof console&&console.log(a,t)}return t}}},C=S,L=(a("f080"),Object(g["a"])(C,l,n,!1,null,null,null));t["default"]=L.exports},"9dad":function(e,t,a){},f080:function(e,t,a){"use strict";var l=a("9dad"),n=a.n(l);n.a}}]);