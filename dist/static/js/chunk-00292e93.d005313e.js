(window["webpackJsonp"]=window["webpackJsonp"]||[]).push([["chunk-00292e93"],{"53c1":function(e,t,n){"use strict";var a=n("b633"),r=n.n(a);r.a},"82f97":function(e,t,n){"use strict";n.r(t);var a=function(){var e=this,t=e.$createElement,n=e._self._c||t;return n("div",{directives:[{name:"loading",rawName:"v-loading",value:e.loading,expression:"loading"}],staticClass:"app-container outbound_manage"},[n("el-form",{attrs:{inline:!0,"label-width":"80px"}},[n("el-form-item",{attrs:{label:"开始日期"}},[n("el-date-picker",{attrs:{type:"daterange","range-separator":"至","start-placeholder":"开始日期","end-placeholder":"结束日期","value-format":"yyyy-MM-dd"},on:{change:e.changeDate},model:{value:e.dateSearch,callback:function(t){e.dateSearch=t},expression:"dateSearch"}})],1),n("el-form-item",{attrs:{label:"订单状态"}},[n("el-select",{attrs:{clearable:"",placeholder:"请选择"},on:{change:e.changeList},model:{value:e.search.status,callback:function(t){e.$set(e.search,"status",t)},expression:"search.status"}},e._l(e.options1,(function(e){return n("el-option",{key:e.id,attrs:{label:e.name,value:e.id}})})),1)],1),n("el-form-item",{attrs:{label:"物料编码"}},[n("el-input",{on:{input:e.changeList},model:{value:e.search.material_no,callback:function(t){e.$set(e.search,"material_no",t)},expression:"search.material_no"}})],1),n("el-form-item",{attrs:{label:"仓库名称"}},[e._v(" "+e._s(e.warehouseName)+" ")])],1),n("el-button",{directives:[{name:"permission",rawName:"v-permission",value:["compoundRubber_plan","norman"],expression:"['compoundRubber_plan','norman']"}],staticClass:"button-right",on:{click:e.normalOutbound}},[e._v("正常出库")]),n("el-button",{directives:[{name:"permission",rawName:"v-permission",value:["compoundRubber_plan","assign"],expression:"['compoundRubber_plan','assign']"}],staticClass:"button-right",on:{click:e.assignOutbound}},[e._v("指定出库")]),n("el-table",{attrs:{border:"",data:e.tableData,size:"mini"}},[n("el-table-column",{attrs:{label:"No",type:"index",align:"center",width:"30"}}),n("el-table-column",{attrs:{label:"仓库名称",align:"center",prop:"name"}}),n("el-table-column",{attrs:{label:"出库类型",align:"center",prop:"inventory_type",width:"65"}}),n("el-table-column",{attrs:{label:"出库单号",align:"center",prop:"order_no"}}),n("el-table-column",{attrs:{label:"托盘号",align:"center",prop:"pallet_no"}}),n("el-table-column",{attrs:{label:"物料编码",align:"center",prop:"material_no"}}),n("el-table-column",{attrs:{label:"出库原因",align:"center",prop:"inventory_reason",width:"50"}}),n("el-table-column",{attrs:{label:"需求数量",align:"center",prop:"need_qty",width:"50"}}),n("el-table-column",{attrs:{label:"出库数量",align:"center",prop:"actual.actual_qty",width:"50"}}),n("el-table-column",{attrs:{label:"实际出库重量",align:"center",prop:"actual.actual_wegit"}}),n("el-table-column",{attrs:{label:"单位",align:"center",prop:"unit",width:"40"}}),n("el-table-column",{attrs:{label:"需求重量",align:"center",prop:"need_weight"}}),n("el-table-column",{attrs:{label:"出库位置",align:"center",prop:"station",width:"40"}}),n("el-table-column",{attrs:{label:"目的地",align:"center",prop:"destination"}}),n("el-table-column",{attrs:{label:"操作",align:"center",width:"220"},scopedSlots:e._u([{key:"default",fn:function(t){return 4===t.row.status?[n("el-button-group",[n("el-button",{directives:[{name:"permission",rawName:"v-permission",value:["compoundRubber_plan","manual"],expression:"['compoundRubber_plan','manual']"}],attrs:{size:"mini",type:"primary"},on:{click:function(n){return e.manualDelivery(t.row)}}},[e._v("人工出库")]),n("el-button",{directives:[{name:"permission",rawName:"v-permission",value:["compoundRubber_plan","change"],expression:"['compoundRubber_plan','change']"}],attrs:{size:"mini",type:"warning"},on:{click:function(n){return e.demandQuantity(t.$index,t.row)}}},[e._v("编辑")]),n("el-button",{directives:[{name:"permission",rawName:"v-permission",value:["compoundRubber_plan","close"],expression:"['compoundRubber_plan','close']"}],attrs:{size:"mini",type:"info"},on:{click:function(n){return e.closePlan(t.$index,t.row)}}},[e._v("关闭")])],1)]:void 0}}],null,!0)}),n("el-table-column",{attrs:{label:"订单状态",align:"center",prop:"",width:"60"},scopedSlots:e._u([{key:"default",fn:function(t){var n=t.row;return[e._v(" "+e._s(e.setOperation(n.status))+" ")]}}])}),n("el-table-column",{attrs:{label:"发起人",align:"center",prop:"created_user"}}),n("el-table-column",{attrs:{label:"发起时间",align:"center",prop:"created_date"}}),n("el-table-column",{attrs:{label:"完成时间",align:"center",prop:"finish_time"}})],1),n("page",{attrs:{total:e.total,"current-page":e.search.page},on:{currentChange:e.currentChange}}),n("el-dialog",{attrs:{title:"编辑",visible:e.dialogVisible,width:"50%","before-close":e.handleClose},on:{"update:visible":function(t){e.dialogVisible=t}}},[n("el-form",{attrs:{inline:!0}},[n("el-form-item",{attrs:{label:"需求数量"}},[n("el-input",{attrs:{placeholder:"需求数量"},model:{value:e.demandQuantityVal,callback:function(t){e.demandQuantityVal=t},expression:"demandQuantityVal"}})],1)],1),n("span",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[n("el-button",{on:{click:function(t){e.dialogVisible=!1}}},[e._v("取 消")]),n("el-button",{attrs:{type:"primary",loading:e.loadingBtn},on:{click:e.submitDemandQuantity}},[e._v("确 定")])],1)],1),n("el-dialog",{attrs:{title:"指定出库",visible:e.assignOutboundDialogVisible,"before-close":e.handleCloseNormal,width:"90%"},on:{"update:visible":function(t){e.assignOutboundDialogVisible=t}}},[n("generate-assign-outbound",{ref:"assignOutbound",attrs:{"warehouse-name":e.warehouseName,"warehouse-info":e.warehouseInfo},on:{visibleMethod:e.visibleMethodNormal,visibleMethodSubmit:e.visibleMethodAssignSubmit}})],1),n("el-dialog",{attrs:{title:"正常出库",visible:e.normalOutboundDialogVisible,"before-close":e.handleCloseNormal},on:{"update:visible":function(t){e.normalOutboundDialogVisible=t}}},[n("generate-normal-outbound",{ref:"normalOutbound",attrs:{"warehouse-name":e.warehouseName,"warehouse-info":e.warehouseInfo},on:{visibleMethod:e.visibleMethodNormal,visibleMethodSubmit:e.visibleMethodSubmit}})],1)],1)},r=[],i=(n("ac1f"),n("841c"),n("96cf"),n("1da1")),o=n("b4ac"),s=n("5cfb"),l=n("1f6c"),u=n("64dc"),c=n("3e51"),d=n("cf45"),b=n("ed08"),m={components:{page:c["a"],GenerateAssignOutbound:o["a"],GenerateNormalOutbound:s["a"]},data:function(){return{loading:!1,search:{page:1},dateSearch:[],dialogVisible:!1,total:0,options1:d["a"].statusList,tableData:[],assignOutboundDialogVisible:!1,normalOutboundDialogVisible:!1,currentIndex:null,demandQuantityVal:"",loadingBtn:!1,rowVal:{},warehouseName:"混炼胶库",warehouseInfo:null}},created:function(){var e=new Date,t=e.getTime()+864e5;this.search.st=Object(b["d"])(),this.search.et=Object(b["d"])(t),this.dateSearch=[this.search.st,this.search.et],this.getListWrehouseInfo(),this.getList()},methods:{getList:function(){var e=this;return Object(i["a"])(regeneratorRuntime.mark((function t(){var n;return regeneratorRuntime.wrap((function(t){while(1)switch(t.prev=t.next){case 0:return t.prev=0,e.loading=!0,e.tableData=[],t.next=5,Object(l["O"])("get",null,{params:e.search});case 5:n=t.sent,e.total=n.count,e.tableData=n.results,e.loading=!1,t.next=14;break;case 11:t.prev=11,t.t0=t["catch"](0),e.loading=!1;case 14:case"end":return t.stop()}}),t,null,[[0,11]])})))()},getListWrehouseInfo:function(){var e=this;return Object(i["a"])(regeneratorRuntime.mark((function t(){var n;return regeneratorRuntime.wrap((function(t){while(1)switch(t.prev=t.next){case 0:return t.prev=0,t.next=3,Object(u["j"])({all:1,name:e.warehouseName});case 3:n=t.sent,e.warehouseInfo=n[0].id,t.next=9;break;case 7:t.prev=7,t.t0=t["catch"](0);case 9:case"end":return t.stop()}}),t,null,[[0,7]])})))()},currentChange:function(e){this.search.page=e,this.getList()},warehouseSelect:function(e){},handleCloseNormal:function(e){this.$refs.normalOutbound&&this.$refs.normalOutbound.creadVal(),this.$refs.assignOutbound&&this.$refs.assignOutbound.creadVal(),e()},changeList:function(){this.search.page=1,this.getList()},changeDate:function(e){this.search.st=e?e[0]:"",this.search.et=e?e[1]:"",this.getList(),this.search.page=1},visibleMethodNormal:function(){this.normalOutboundDialogVisible=!1,this.assignOutboundDialogVisible=!1},visibleMethodSubmit:function(e){var t=this;return Object(i["a"])(regeneratorRuntime.mark((function n(){return regeneratorRuntime.wrap((function(n){while(1)switch(n.prev=n.next){case 0:return n.prev=0,n.next=3,Object(l["O"])("post",null,{data:[e]});case 3:t.$message.success("操作成功"),t.normalOutboundDialogVisible=!1,t.getList(),t.$refs.normalOutbound.loadingBtn=!1,t.$refs.normalOutbound.creadVal(),n.next=13;break;case 10:n.prev=10,n.t0=n["catch"](0),t.$refs.normalOutbound.loadingBtn=!1;case 13:case"end":return n.stop()}}),n,null,[[0,10]])})))()},visibleMethodAssignSubmit:function(e){var t=this;return Object(i["a"])(regeneratorRuntime.mark((function n(){return regeneratorRuntime.wrap((function(n){while(1)switch(n.prev=n.next){case 0:return n.prev=0,n.next=3,Object(l["O"])("post",null,{data:e});case 3:t.$message.success("操作成功"),t.assignOutboundDialogVisible=!1,t.$refs.assignOutbound.creadVal(),t.getList(),n.next=12;break;case 9:n.prev=9,n.t0=n["catch"](0),t.$refs.assignOutbound.loadingBtn=!1;case 12:case"end":return n.stop()}}),n,null,[[0,9]])})))()},handleClose:function(e){e()},normalOutbound:function(){d["a"].normalOutboundSwitch?this.normalOutboundDialogVisible=!0:this.$message.info("该功能wms暂时无法使用")},assignOutbound:function(){this.assignOutboundDialogVisible=!0},submitDemandQuantity:function(){var e=this;return Object(i["a"])(regeneratorRuntime.mark((function t(){var n,a;return regeneratorRuntime.wrap((function(t){while(1)switch(t.prev=t.next){case 0:if(t.prev=0,n=e.tableData[e.currentIndex],e.demandQuantityVal||0===e.demandQuantityVal){t.next=5;break}return e.$message.info("需求数量不可为空"),t.abrupt("return");case 5:return a={inventory_type:3333,need_qty:e.demandQuantityVal,order_no:"order_no",warehouse_info:n.warehouse_info},e.loadingBtn=!0,t.next=9,Object(l["O"])("put",n.id,{data:a});case 9:e.dialogVisible=!1,e.loadingBtn=!1,e.getList(),t.next=17;break;case 14:t.prev=14,t.t0=t["catch"](0),e.loadingBtn=!1;case 17:case"end":return t.stop()}}),t,null,[[0,14]])})))()},manualDelivery:function(e){var t=this;this.$confirm("确定出库?","提示",{confirmButtonText:"确定",cancelButtonText:"取消",type:"warning"}).then(Object(i["a"])(regeneratorRuntime.mark((function n(){var a;return regeneratorRuntime.wrap((function(n){while(1)switch(n.prev=n.next){case 0:return a={warehouse_info:e.warehouse_info,inventory_type:e.inventory_type,order_no:e.order_no,material_no:e.material_no,wegit:e.need_weight||"",created_date:e.created_date,pallet_no:e.pallet_no||"",inventory_reason:e.inventory_reason||""},t.loading=!0,n.next=4,Object(l["O"])("put",e.id,{data:a});case 4:t.$message.success("操作成功"),t.getList();case 6:case"end":return n.stop()}}),n)})))).catch((function(){t.loading=!1}))},demandQuantity:function(e,t){this.currentIndex=e,this.dialogVisible=!0,this.demandQuantityVal=t.need_qty||""},closePlan:function(e,t){var n=this;this.$confirm("确定关闭?","提示",{confirmButtonText:"确定",cancelButtonText:"取消",type:"warning"}).then(Object(i["a"])(regeneratorRuntime.mark((function e(){var a;return regeneratorRuntime.wrap((function(e){while(1)switch(e.prev=e.next){case 0:return a={status:5,order_no:"order_no",warehouse_info:n.warehouseInfo},n.loading=!0,e.next=4,Object(l["O"])("put",t.id,{data:a});case 4:n.$message.success("操作成功"),n.getList();case 6:case"end":return e.stop()}}),e)})))).catch((function(){n.loading=!1}))},setOperation:function(e){switch(e){case 1:return"完成";case 2:return"执行中";case 3:return"失败";case 4:return"新建";case 5:return"关闭"}}}},p=m,h=(n("53c1"),n("2877")),g=Object(h["a"])(p,a,r,!1,null,null,null);t["default"]=g.exports},b633:function(e,t,n){}}]);