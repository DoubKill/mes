(window["webpackJsonp"]=window["webpackJsonp"]||[]).push([["chunk-4ff521f4","chunk-6f21f21a"],{"129f":function(e,t){e.exports=Object.is||function(e,t){return e===t?0!==e||1/e===1/t:e!=e&&t!=t}},"1c7e2":function(e,t,a){"use strict";a.r(t);var l=function(){var e=this,t=e.$createElement,a=e._self._c||t;return a("div",{directives:[{name:"loading",rawName:"v-loading",value:e.loading,expression:"loading"}]},[a("el-form",{attrs:{inline:!0}},[a("el-form-item",{attrs:{label:"时间"}},[a("el-date-picker",{attrs:{type:"date",placeholder:"选择日期","value-format":"yyyy-MM-dd"},on:{change:e.changeList},model:{value:e.getParams.start_time,callback:function(t){e.$set(e.getParams,"start_time",t)},expression:"getParams.start_time"}})],1),e.isDialog?e._e():a("el-form-item",{attrs:{label:"订单状态"}},[a("el-select",{attrs:{clearable:"",placeholder:"请选择"},on:{change:e.changeList},model:{value:e.getParams.status,callback:function(t){e.$set(e.getParams,"status",t)},expression:"getParams.status"}},e._l(e.options1,(function(e){return a("el-option",{key:e.id,attrs:{label:e.name,value:e.id}})})),1)],1),e.isDialog?e._e():a("el-form-item",{attrs:{label:"物料编码"}},[a("material-code-select",{on:{changeSelect:e.materialCodeFun}})],1),a("el-form-item",{attrs:{label:"发货类型"}},[a("deliverTypeSelect",{on:{changeSelect:e.deliverTypeSelectFun}})],1),a("el-form-item",{attrs:{label:"目的地"}},[a("destinationSelect",{on:{changeSelect:e.destinationSelectFun}})],1),e.isDialog?e._e():a("el-form-item",{staticStyle:{float:"right"}},[a("el-button",{directives:[{name:"permission",rawName:"v-permission",value:["delivery_plan","add"],expression:"['delivery_plan', 'add']"}],on:{click:e.showCreateDialog}},[e._v("新建")])],1)],1),a("el-table",{ref:"multipleTable",staticStyle:{width:"100%"},attrs:{border:"","cell-style":e.cellStyle,data:e.tableData,"row-key":e.getRowKeys},on:{"selection-change":e.handleSelectionChange}},[e.isDialog?a("el-table-column",{attrs:{type:"selection",width:"40","reserve-selection":!0}}):e._e(),a("el-table-column",{attrs:{label:"No",type:"index",align:"center"}}),a("el-table-column",{attrs:{label:"目的地",align:"center",prop:"dispatch_location_name"}}),a("el-table-column",{attrs:{label:"发货单号",align:"center",prop:"order_no"}}),a("el-table-column",{attrs:{label:"发货类型",align:"center",prop:"dispatch_type_name"}}),a("el-table-column",{attrs:{label:"物料编码",align:"center",prop:"material_name"}}),a("el-table-column",{attrs:{label:"发货数量",align:"center",prop:"need_qty"}}),a("el-table-column",{attrs:{label:"已发数量",align:"center",prop:"actual_qty"}}),a("el-table-column",{attrs:{label:"发货重量",align:"center",prop:"need_weight"}}),a("el-table-column",{attrs:{label:"已发重量",align:"center",prop:"actual_weight"}}),a("el-table-column",{attrs:{label:"订单状态",align:"center",prop:"status_name"}}),e.isDialog?e._e():a("el-table-column",{attrs:{label:"操作",width:"134",align:"center"},scopedSlots:e._u([{key:"default",fn:function(t){return[a("el-button-group",[2==t.row.status||4==t.row.status?a("el-button",{directives:[{name:"permission",rawName:"v-permission",value:["delivery_plan","delete"],expression:"['delivery_plan', 'delete']"}],attrs:{size:"mini"},on:{click:function(a){return e.handleClose(t.row)}}},[e._v("关闭")]):e._e(),4==t.row.status?a("el-button",{directives:[{name:"permission",rawName:"v-permission",value:["delivery_plan","change"],expression:"['delivery_plan', 'change']"}],attrs:{size:"mini",type:"blue"},on:{click:function(a){return e.showEditDialog(t.row)}}},[e._v("编辑 ")]):e._e()],1)]}}],null,!1,1594149050)}),a("el-table-column",{attrs:{label:"发起人",align:"center",prop:"dispatch_user"}}),a("el-table-column",{attrs:{label:"发起时间",align:"center",prop:"start_time"}}),e.isDialog?e._e():a("el-table-column",{attrs:{label:"完成时间",align:"center",prop:"fin_time"}})],1),a("page",{attrs:{total:e.total,"current-page":e.getParams.page},on:{currentChange:e.currentChange}}),a("el-dialog",{attrs:{title:"新建发货计划",visible:e.createDialogVisible,"close-on-click-modal":!1},on:{"update:visible":function(t){e.createDialogVisible=t}}},[a("el-form",{ref:"Form",attrs:{rules:e.rules,"label-width":"100px",model:e.createForm}},[a("el-form-item",{attrs:{label:"目的地",prop:"dispatch_location"}},[a("destinationSelect",{ref:"destinationSelect",on:{changeSelect:e.destinationCreateForm}})],1),a("el-form-item",{attrs:{label:"发货类型",prop:"dispatch_type"}},[a("deliverTypeSelect",{ref:"deliverTypeSelect",on:{changeSelect:e.deliverTypeCreateForm}})],1),a("el-form-item",{attrs:{label:"物料编码",prop:"material"}},[a("material-code-select",{ref:"materialCodeSelect",on:{changeSelect:e.materialCreateForm}})],1),a("el-form-item",{attrs:{label:"发货数量",prop:"need_qty"}},[a("el-input",{staticStyle:{width:"200px"},attrs:{type:"age"},model:{value:e.createForm.need_qty,callback:function(t){e.$set(e.createForm,"need_qty",e._n(t))},expression:"createForm.need_qty"}})],1),a("el-form-item",{attrs:{label:"发货重量",prop:"need_weight"}},[a("el-input-number",{attrs:{min:0,step:.01,"step-strictly":""},model:{value:e.createForm.need_weight,callback:function(t){e.$set(e.createForm,"need_weight",t)},expression:"createForm.need_weight"}})],1)],1),a("div",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[a("el-button",{on:{click:function(t){e.createDialogVisible=!1}}},[e._v("取 消")]),a("el-button",{attrs:{type:"primary"},on:{click:function(t){return e.handleCreate()}}},[e._v("确 定")])],1)],1),a("el-dialog",{attrs:{title:"编辑发货计划",visible:e.editDialogVisible,"close-on-click-modal":!1},on:{"update:visible":function(t){e.editDialogVisible=t}}},[a("el-form",{ref:"Form",attrs:{rules:e.rules,"label-width":"100px",model:e.editForm}},[a("el-form-item",{attrs:{label:"目的地",prop:"dispatch_location"}},[a("destinationSelect",{attrs:{"default-val":e.editForm.dispatch_location,"created-is":!0},on:{changeSelect:e.destinationEditForm}})],1),a("el-form-item",{attrs:{label:"发货类型",prop:"dispatch_type"}},[a("deliverTypeSelect",{attrs:{"default-val":e.editForm.dispatch_type,"created-is":!0},on:{changeSelect:e.deliverTypeEditForm}})],1),a("el-form-item",{attrs:{label:"发货数量",prop:"need_qty"}},[a("el-input",{staticStyle:{width:"200px"},attrs:{type:"age"},model:{value:e.editForm.need_qty,callback:function(t){e.$set(e.editForm,"need_qty",e._n(t))},expression:"editForm.need_qty"}})],1),a("el-form-item",{attrs:{label:"发货重量",prop:"need_weight"}},[a("el-input-number",{model:{value:e.editForm.need_weight,callback:function(t){e.$set(e.editForm,"need_weight",t)},expression:"editForm.need_weight"}})],1)],1),a("div",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[a("el-button",{on:{click:function(t){e.editDialogVisible=!1}}},[e._v("取 消")]),a("el-button",{attrs:{type:"primary"},on:{click:function(t){return e.handleEdit()}}},[e._v("确 定")])],1)],1)],1)},i=[],r=(a("4de4"),a("c740"),a("4160"),a("caad"),a("159b"),a("96cf"),a("1da1")),n=a("f060"),o=a("ed08"),s=a("3e51"),c=a("cf45"),u=a("4cad"),d=a("19c7"),m=a("1313"),h={components:{page:s["a"],MaterialCodeSelect:u["a"],deliverTypeSelect:d["a"],destinationSelect:m["a"]},props:{isDialog:{type:Boolean,default:!1},materialNo:{type:String,default:null},show:{type:Boolean,default:!1},defalutVal:{type:Array,default:function(){return[]}}},data:function(){return{tableData:[],options1:c["a"].statusList,getParams:{start_time:Object(o["d"])(),page:1},createDialogVisible:!1,createForm:{},editDialogVisible:!1,editForm:{},rules:{dispatch_location:[{required:!0,message:"不能为空",trigger:"blur"}],dispatch_type:[{required:!0,message:"不能为空",trigger:"blur"}],material:[{required:!0,message:"不能为空",trigger:"blur"}],need_qty:[{required:!0,message:"不能为空",trigger:"blur"},{type:"number",message:"请输入合法整数",trigger:"blur"}],need_weight:[{required:!0,message:"不能为空",trigger:"blur"},{type:"number",message:"请输入合法数字",trigger:"blur"}]},total:1,handleSelection:[],loading:!1}},watch:{show:function(e){e&&(this.$refs.multipleTable.clearSelection(),this.getParams.page=1,this.getParams.material_no=this.materialNo||null,this.getTableData())}},updated:function(){},created:function(){this.getParams.material_no=this.materialNo||null,this.getTableData()},methods:{getTableData:function(){var e=this;return Object(r["a"])(regeneratorRuntime.mark((function t(){return regeneratorRuntime.wrap((function(t){while(1)switch(t.prev=t.next){case 0:return e.loading=!0,t.next=3,Object(n["e"])(e.getParams).then((function(t){e.loading=!1,e.tableData=t.results,e.total=t.count,e.isDialog&&(e.tableData=e.tableData.filter((function(e){return[4,2].includes(e.status)}))),e.tableData.length>0&&e.defalutVal&&e.defalutVal.length>0&&e.tableData.forEach((function(t,a){e.defalutVal.findIndex((function(e){return e.id===t.id}))>-1&&e.$refs.multipleTable.toggleRowSelection(t)}))})).catch((function(){e.loading=!1}));case 3:case"end":return t.stop()}}),t)})))()},changeList:function(){this.getParams.page=1,this.getTableData()},materialCodeFun:function(e){this.getParams.material=e,this.getParams.page=1,this.getTableData()},deliverTypeSelectFun:function(e){this.getParams.dispatch_type=e,this.getParams.page=1,this.getTableData()},destinationSelectFun:function(e){this.getParams.dispatch_location=e,this.getParams.page=1,this.getTableData()},clearCreateForm:function(){this.$refs.destinationSelect&&(this.$refs.destinationSelect.value=""),this.$refs.deliverTypeSelect&&(this.$refs.deliverTypeSelect.value=""),this.$refs.materialCodeSelect&&(this.$refs.materialCodeSelect.value=""),this.createForm={dispatch_location:null,dispatch_type:null,material:null}},showCreateDialog:function(){var e=this;this.clearCreateForm(),this.createDialogVisible=!0,this.$nextTick((function(){e.$refs.Form.clearValidate()}))},materialCreateForm:function(e){this.createForm.material=e},deliverTypeCreateForm:function(e){this.createForm.dispatch_type=e},destinationCreateForm:function(e){this.createForm.dispatch_location=e},handleCreate:function(){var e=this;this.$refs.Form.validate((function(t){t&&Object(n["g"])(e.createForm).then((function(t){e.createDialogVisible=!1,e.$message("创建成功"),e.getParams.page=1,e.getTableData()}))}))},showEditDialog:function(e){var t=this;this.editForm=Object.assign({},e),this.editDialogVisible=!0,this.$nextTick((function(){t.$refs.Form.clearValidate()}))},destinationEditForm:function(e){this.editForm.dispatch_location=e},deliverTypeEditForm:function(e){this.editForm.dispatch_type=e},handleEdit:function(){var e=this;this.$refs.Form.validate((function(t){t&&Object(n["i"])(e.editForm,e.editForm.id).then((function(t){e.editDialogVisible=!1,e.$message("修改成功"),e.getParams.page=1,e.getTableData()}))}))},handleClose:function(e){var t=this;console.log(e.status);var a=2===e.status?"执行中":"新建";this.$confirm("此操作将关闭 "+a+" 的发货单单"+e.order_no+", 是否继续?","提示",{confirmButtonText:"确定",cancelButtonText:"取消",type:"warning"}).then((function(){Object(n["b"])(e.id).then((function(e){t.$message({type:"success",message:"操作成功!"}),t.getParams.page=1,t.getTableData()})).catch((function(){}))}))},currentChange:function(e){this.getParams.page=e,this.getTableData()},handleSelectionChange:function(e){this.handleSelection=e},clearReceiveSelect:function(){this.$refs.multipleTable.clearSelection()},getRowKeys:function(e){return e.id},cellStyle:function(e){var t=e.row,a=e.column,l=(e.rowIndex,e.columnIndex,a.property);if(t[l]&&"status_name"===l){if("关闭"===t[l])return"color: #888888";if("新建"===t[l])return"color: #000093";if("执行中"===t[l])return"color: #F5A623";if("完成"===t[l])return"color: #7ED321";if("失败"===t[l])return"color: #FF0000"}}}},f=h,p=a("2877"),g=Object(p["a"])(f,l,i,!1,null,null,null);t["default"]=g.exports},"25f6":function(e,t,a){"use strict";a.d(t,"a",(function(){return r}));var l=a("b775"),i=a("99b1");function r(e){return Object(l["a"])({url:i["a"].MaterialInventoryManage,method:"get",params:e})}},"5cfb":function(e,t,a){"use strict";var l=function(){var e=this,t=e.$createElement,a=e._self._c||t;return a("div",{staticClass:"generate_normal_outbound"},[a("el-form",{ref:"ruleForm",attrs:{model:e.ruleForm,rules:e.rules,"label-width":"140px"}},[a("el-form-item",{attrs:{label:"仓库名称"}},[e._v(" "+e._s(e.warehouseName)+" ")]),a("el-form-item",{attrs:{label:"仓库位置",prop:"station"}},[a("stationInfoWarehouse",{ref:"stationInfoWarehouseRef",attrs:{"warehouse-name":e.warehouseName,"start-using":!0},on:{changSelect:e.changSelectStation}})],1),a("el-form-item",{attrs:{label:"品质状态",prop:"quality_status"}},[a("el-select",{attrs:{placeholder:"请选择"},model:{value:e.ruleForm.quality_status,callback:function(t){e.$set(e.ruleForm,"quality_status",t)},expression:"ruleForm.quality_status"}},e._l(e.options,(function(e){return a("el-option",{key:e,attrs:{label:e,value:e}})})),1)],1),a("el-form-item",{attrs:{label:"物料编码",prop:"material_no"}},[a("materialCodeSelect",{attrs:{"store-name":e.warehouseName,"default-val":e.ruleForm.material_no},on:{changSelect:e.materialCodeFun}})],1),a("el-form-item",{attrs:{label:"可用库存数",prop:"c"}},[a("el-input",{attrs:{disabled:""},model:{value:e.ruleForm.c,callback:function(t){e.$set(e.ruleForm,"c",t)},expression:"ruleForm.c"}})],1),a("el-form-item",{attrs:{label:"需求数量("+("帘布库"===e.warehouseName?"托":"车")+")",prop:"need_qty"}},[a("el-input-number",{attrs:{"controls-position":"right",max:e.ruleForm.c},model:{value:e.ruleForm.need_qty,callback:function(t){e.$set(e.ruleForm,"need_qty",t)},expression:"ruleForm.need_qty"}})],1),a("el-form-item",{attrs:{label:"需求重量"}},[a("el-input-number",{attrs:{"controls-position":"right",precision:3},model:{value:e.ruleForm.need_weight,callback:function(t){e.$set(e.ruleForm,"need_weight",t)},expression:"ruleForm.need_weight"}})],1),"终炼胶出库计划"===e.$route.meta.title?a("el-form-item",{attrs:{label:"关联发货计划"}},[e._v(" "+e._s(e.ruleForm.deliveryPlan)+" "),a("el-button",{attrs:{type:"primary"},on:{click:e.deliverClick}},[e._v("请添加")])],1):e._e(),"混炼胶出库计划"===e.$route.meta.title?a("el-form-item",{attrs:{label:"机台号"}},[a("EquipSelect",{ref:"EquipSelect",attrs:{"is-multiple":!0},on:{equipSelected:e.equipSelected}})],1):e._e()],1),a("div",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[a("el-button",{on:{click:function(t){return e.visibleMethod(!0)}}},[e._v("取 消")]),a("el-button",{attrs:{type:"primary",loading:e.loadingBtn},on:{click:function(t){return e.visibleMethod(!1)}}},[e._v("确 定")])],1),a("el-dialog",{attrs:{title:"发货计划管理",visible:e.dialogVisible,width:"90%","append-to-body":""},on:{"update:visible":function(t){e.dialogVisible=t}}},[a("receiveList",{ref:"receiveList",attrs:{show:e.dialogVisible,"defalut-val":e.handleSelection,"is-dialog":!0,"material-no":e.ruleForm.material_no}}),a("span",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[a("el-button",{on:{click:function(t){e.dialogVisible=!1}}},[e._v("取 消")]),a("el-button",{attrs:{type:"primary"},on:{click:e.sureDeliveryPlan}},[e._v("确 定")])],1)],1)],1)},i=[],r=(a("4160"),a("caad"),a("b0c0"),a("a9e3"),a("159b"),a("621a5")),n=a("a5db"),o=a("1c7e2"),s=a("8448"),c={components:{EquipSelect:s["a"],materialCodeSelect:r["a"],stationInfoWarehouse:n["a"],receiveList:o["default"]},props:{warehouseName:{type:String,default:function(){return""}},warehouseInfo:{type:Number,default:function(){return null}}},data:function(){var e=this,t=function(e,t,a,l,i){l?a():a(new Error(i))};return{ruleForm:{warehouse_name:this.warehouseName,warehouse_info:this.warehouseInfo,material_no:"",inventory_type:"正常出库",order_no:"order_no",status:4,need_weight:void 0},rules:{material_no:[{required:!0,message:"请输入物料编码",trigger:"blur"}],quality_status:[{required:!0,message:"请选择品质状态",trigger:"change"}],c:[{required:!0,trigger:"blur",validator:function(a,l,i){t(a,l,i,e.ruleForm.c,"无库存数")}}],station:[{required:!0,trigger:"blur",validator:function(a,l,i){t(a,l,i,e.ruleForm.station,"仓库位置")}}],need_qty:[{required:!0,message:"请输入需求数量",trigger:"blur"}]},visible:!1,loadingBtn:null,dialogVisible:!1,handleSelection:[],options:["终炼胶库","混炼胶库"].includes(this.warehouseName)?["一等品","三等品"]:["合格品","不合格品"]}},watch:{},created:function(){},methods:{creadVal:function(){this.$refs.ruleForm.resetFields(),this.$refs.receiveList&&this.$refs.receiveList.clearReceiveSelect(),this.$refs.EquipSelect&&(this.$refs.EquipSelect.equipId=null),this.ruleForm.dispatch=[],this.ruleForm.equip=[],this.handleSelection=[],this.ruleForm.deliveryPlan="",this.loadingBtn=!1,this.$refs.stationInfoWarehouseRef&&(this.$refs.stationInfoWarehouseRef.value=null)},materialCodeFun:function(e){this.ruleForm.material_no=e.material_no||null,this.ruleForm.c=e.all_qty||null,this.$refs.receiveList&&this.$refs.receiveList.clearReceiveSelect(),this.ruleForm.deliveryPlan="",this.handleSelection=[]},visibleMethod:function(e){var t=this;if(e)this.creadVal(),this.$emit("visibleMethod");else{var a=[];this.handleSelection&&this.handleSelection.length>0?(this.handleSelection.forEach((function(e){a.push(e.id)})),this.$set(this.ruleForm,"dispatch",a)):this.$set(this.ruleForm,"dispatch",[]),this.$refs.ruleForm.validate((function(e){if(!e)return!1;t.loadingBtn=!0,t.$emit("visibleMethodSubmit",t.ruleForm)}))}},changSelectStation:function(e){this.ruleForm.station=e?e.name:""},deliverClick:function(){this.ruleForm.material_no?this.dialogVisible=!0:this.$message.info("请选择物料编码")},sureDeliveryPlan:function(){var e=this,t=0;this.handleSelection=this.$refs.receiveList.handleSelection,this.ruleForm.deliveryPlan="",this.handleSelection.forEach((function(a){e.ruleForm.deliveryPlan+=a.order_no+";",t+=a.need_qty})),t>this.ruleForm.c?this.$message.info("物料可用库存数不足"):t<this.ruleForm.c&&this.$message.info("物料可用库存数有余"),this.dialogVisible=!1},equipSelected:function(e){e&&e.length>0?this.$set(this.ruleForm,"equip",e):Object.prototype.hasOwnProperty.call(this.ruleForm,"equip")&&delete this.ruleForm.equip}}},u=c,d=(a("8e49"),a("2877")),m=Object(d["a"])(u,l,i,!1,null,null,null);t["a"]=m.exports},"64dc":function(e,t,a){"use strict";a.d(t,"l",(function(){return r})),a.d(t,"j",(function(){return n})),a.d(t,"b",(function(){return o})),a.d(t,"h",(function(){return s})),a.d(t,"e",(function(){return c})),a.d(t,"a",(function(){return u})),a.d(t,"i",(function(){return d})),a.d(t,"f",(function(){return m})),a.d(t,"k",(function(){return h})),a.d(t,"c",(function(){return f})),a.d(t,"g",(function(){return p})),a.d(t,"d",(function(){return g}));var l=a("b775"),i=a("99b1");function r(){return Object(l["a"])({url:i["a"].WarehouseNamesUrl,method:"get"})}function n(e){return Object(l["a"])({url:i["a"].WarehouseInfoUrl,method:"get",params:e})}function o(e,t,a){return Object(l["a"])({url:t?i["a"].WarehouseInfoUrl+t+"/":i["a"].WarehouseInfoUrl,method:e,data:a})}function s(e){return Object(l["a"])({url:i["a"].WarehouseInfoUrl+e+"/reversal_use_flag/",method:"put"})}function c(e){return Object(l["a"])({url:i["a"].StationInfoUrl,method:"get",params:e})}function u(e,t,a){return Object(l["a"])({url:t?i["a"].StationInfoUrl+t+"/":i["a"].StationInfoUrl,method:e,data:a})}function d(e){return Object(l["a"])({url:i["a"].StationInfoUrl+e+"/reversal_use_flag/",method:"put"})}function m(){return Object(l["a"])({url:i["a"].StationTypesUrl,methods:"get"})}function h(e){return Object(l["a"])({url:i["a"].WarehouseMaterialTypeUrl,method:"get",params:e})}function f(e,t,a){return Object(l["a"])({url:t?i["a"].WarehouseMaterialTypeUrl+t+"/":i["a"].WarehouseMaterialTypeUrl,method:e,data:a})}function p(e){return Object(l["a"])({url:i["a"].WarehouseMaterialTypeUrl+e+"/reversal_use_flag/",method:"put"})}function g(){return Object(l["a"])({url:i["a"].MaterialTypesUrl,methods:"get"})}},"66ad":function(e,t,a){"use strict";a.d(t,"b",(function(){return r})),a.d(t,"c",(function(){return n})),a.d(t,"f",(function(){return o})),a.d(t,"a",(function(){return s})),a.d(t,"e",(function(){return c})),a.d(t,"d",(function(){return u})),a.d(t,"g",(function(){return d}));var l=a("b775"),i=a("99b1");function r(e){return Object(l["a"])({url:i["a"].EquipUrl,method:"get",params:e})}function n(e){return Object(l["a"])({url:i["a"].PalletFeedBacksUrl,method:"get",params:e})}function o(e){return Object(l["a"])({url:i["a"].TrainsFeedbacksUrl,method:"get",params:e})}function s(e){return Object(l["a"])({url:i["a"].EchartsListUrl,method:"get",params:e})}function c(e){return Object(l["a"])({url:i["a"].ProductActualUrl,method:"get",params:e})}function u(e){return Object(l["a"])({url:i["a"].PalletFeedbacksUrl,method:"get",params:e})}function d(e){return Object(l["a"])({url:i["a"].ProductDayPlanNoticeUrl,method:"post",id:e})}},"6d7d":function(e,t,a){"use strict";var l=a("abc3"),i=a.n(l);i.a},"841c":function(e,t,a){"use strict";var l=a("d784"),i=a("825a"),r=a("1d80"),n=a("129f"),o=a("14c3");l("search",1,(function(e,t,a){return[function(t){var a=r(this),l=void 0==t?void 0:t[e];return void 0!==l?l.call(t,a):new RegExp(t)[e](String(a))},function(e){var l=a(t,e,this);if(l.done)return l.value;var r=i(e),s=String(this),c=r.lastIndex;n(c,0)||(r.lastIndex=0);var u=o(r,s);return n(r.lastIndex,c)||(r.lastIndex=c),null===u?-1:u.index}]}))},"87a12":function(e,t,a){},"8e49":function(e,t,a){"use strict";var l=a("87a12"),i=a.n(l);i.a},abc3:function(e,t,a){},b4ac:function(e,t,a){"use strict";var l=function(){var e=this,t=e.$createElement,a=e._self._c||t;return a("div",{directives:[{name:"loading",rawName:"v-loading",value:e.loading,expression:"loading"}],staticClass:"app-container"},[a("el-form",{attrs:{inline:!0}},[a("el-form-item",{attrs:{label:"仓库名称"}},[e._v(" "+e._s(e.warehouseName)+" ")]),a("el-form-item",{attrs:{label:"物料编码"}},[a("el-input",{on:{input:e.changeSearch},model:{value:e.getParams.material_no,callback:function(t){e.$set(e.getParams,"material_no",t)},expression:"getParams.material_no"}})],1),a("el-form-item",{attrs:{label:"品质状态"}},[a("el-select",{attrs:{placeholder:"请选择",clearable:""},on:{change:e.changeSearch},model:{value:e.getParams.quality_status,callback:function(t){e.$set(e.getParams,"quality_status",t)},expression:"getParams.quality_status"}},e._l(e.options,(function(e){return a("el-option",{key:e,attrs:{label:e,value:e}})})),1)],1)],1),a("el-table",{ref:"multipleTable",staticStyle:{width:"100%"},attrs:{border:"",data:e.tableData,"row-key":e.getRowKeys},on:{"selection-change":e.handleSelectionChange}},[a("el-table-column",{attrs:{type:"selection",width:"40","reserve-selection":!0}}),a("el-table-column",{attrs:{label:"物料类型",align:"center",prop:"material_type"}}),a("el-table-column",{attrs:{label:"物料编码",align:"center",prop:"material_no"}}),a("el-table-column",{attrs:{label:"lot",align:"center",prop:"lot_no"}}),a("el-table-column",{attrs:{label:"托盘号",align:"center",prop:"container_no"}}),a("el-table-column",{attrs:{label:"库存位",align:"center",prop:"location"}}),"终炼胶库"===e.warehouseName?a("el-table-column",{attrs:{width:"60",label:"车次",align:"center",prop:""},scopedSlots:e._u([{key:"default",fn:function(t){var a=t.row;return[e._v(" "+e._s(a.qty)+" ")]}}],null,!1,1845176995)}):e._e(),a("el-table-column",{attrs:{label:"总重量",align:"center",prop:"total_weight"}}),a("el-table-column",{attrs:{label:"品质状态",align:"center"},scopedSlots:e._u([{key:"default",fn:function(t){var l=t.row;return["帘布库出库计划"===e.$route.meta.title?a("span",[e._v(e._s(l.quality_status))]):a("span",[e._v(e._s(l.quality_level))])]}}])}),a("el-table-column",{attrs:{label:"入库时间",align:"center",prop:"in_storage_time"}}),a("el-table-column",{attrs:{label:"机台号",width:"50",align:"center",prop:"equip_no"}}),a("el-table-column",{attrs:{label:"车号",align:"center",prop:"memo"}}),a("el-table-column",{attrs:{label:"出库位置选择",align:"center"},scopedSlots:e._u([{key:"default",fn:function(t){return[a("stationInfoWarehouse",{attrs:{"warehouse-name":e.warehouseName,"start-using":!0},on:{changSelect:function(a){return e.selectStation(a,t.$index)}}})]}}])}),"终炼胶出库计划"===e.$route.meta.title?a("el-table-column",{attrs:{label:"关联发货计划",align:"center",width:"120"},scopedSlots:e._u([{key:"default",fn:function(t){return[e._v(" "+e._s(t.row.deliveryPlan)+" "),a("el-button",{attrs:{size:"mini",type:"primary"},on:{click:function(a){return e.deliverClick(t.row,t.$index)}}},[e._v("添加发货计划")])]}}],null,!1,2461161841)}):e._e(),"混炼胶出库计划"===e.$route.meta.title?a("el-table-column",{attrs:{label:"机台号",align:"center","min-width":"100"},scopedSlots:e._u([{key:"default",fn:function(t){return[a("EquipSelect",{attrs:{"is-multiple":!0},on:{equipSelected:function(a){return e.equipSelected(a,t.$index)}}})]}}],null,!1,3155262495)}):e._e()],1),a("page",{attrs:{total:e.total,"current-page":e.getParams.page},on:{currentChange:e.currentChange}}),a("div",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[a("el-button",{on:{click:function(t){return e.visibleMethod(!0)}}},[e._v("取 消")]),a("el-button",{attrs:{type:"primary",loading:e.loadingBtn},on:{click:function(t){return e.visibleMethod(!1)}}},[e._v("确 定")])],1),a("el-dialog",{attrs:{title:"发货计划管理",visible:e.dialogVisible,width:"90%","append-to-body":""},on:{"update:visible":function(t){e.dialogVisible=t}}},[a("receiveList",{ref:"receiveList",attrs:{show:e.dialogVisible,"is-dialog":!0,"defalut-val":e.handleSelection,"material-no":e.material_no_current}}),a("span",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[a("el-button",{on:{click:function(t){e.dialogVisible=!1}}},[e._v("取 消")]),a("el-button",{attrs:{type:"primary"},on:{click:e.sureDeliveryPlan}},[e._v("确 定")])],1)],1)],1)},i=[],r=(a("4160"),a("caad"),a("b0c0"),a("a9e3"),a("159b"),a("25f6")),n=a("3e51"),o=a("a5db"),s=a("1c7e2"),c=a("8448"),u={components:{EquipSelect:c["a"],page:n["a"],stationInfoWarehouse:o["a"],receiveList:s["default"]},props:{warehouseName:{type:String,default:""},warehouseInfo:{type:Number,default:null}},data:function(){return{tableData:[],getParams:{page:1,location_status:"有货货位",material_type:"",material_no:"",container_no:"",warehouse_name:this.warehouseName},currentPage:1,total:0,options:["终炼胶库","混炼胶库"].includes(this.warehouseName)?["一等品","三等品"]:["合格品","不合格品"],loading:!1,multipleSelection:[],loadingBtn:!1,dialogVisible:!1,material_no_current:"",currentIndex:null,handleSelection:[]}},computed:{},created:function(){this.getTableData()},methods:{getTableData:function(){var e=this;this.loading=!0,Object(r["a"])(this.getParams).then((function(t){e.tableData=t.results,e.total=t.count,e.tableData.forEach((function(t){e.$set(t,"_DeliveryPlan",[])})),e.loading=!1})).catch((function(){e.loading=!1}))},currentChange:function(e){this.currentPage=e,this.getParams.page=e,this.getTableData()},changeSearch:function(){this.getParams.page=1,this.getTableData()},changeMaterialType:function(e){this.getParams.material_type=e,this.getParams.page=1,this.getTableData()},warehouseSelect:function(e){this.getParams.page=1,this.getParams.warehouse_name=e,this.getTableData()},creadVal:function(){this.$refs.multipleTable.clearSelection(),this.loadingBtn=!1,this.multipleSelection=[],this.tableData.forEach((function(e){e.equipNoArr=null,e._DeliveryPlan=null,e.deliveryPlan=null}))},visibleMethod:function(e){var t=this;if(e)this.creadVal(),this.$emit("visibleMethod");else{if(0===this.multipleSelection.length)return;var a=!1,l=[];if(this.multipleSelection.forEach((function(e){e.station?l.push({order_no:"order_no",pallet_no:e.container_no,need_qty:e.qty,need_weight:e.total_weight,material_no:e.material_no,inventory_type:"指定出库",inventory_reason:e.inventory_reason,unit:e.unit,status:4,warehouse_info:t.warehouseInfo,quality_status:e.quality_status,dispatch:e.dispatch||[],equip:e.equip||[],location:e.location,station:e.station}):a=!0})),a)return void this.$message.info("出库位置必填");this.loadingBtn=!0,this.$emit("visibleMethodSubmit",l)}},changSelectStation:function(e){this.getParams.station=e?e.name:""},handleSelectionChange:function(e){e.length>0&&(this.multipleSelection=e)},getRowKeys:function(e){return e.id},sureDeliveryPlan:function(){var e=this;this.dialogVisible=!1,this.tableData[this.currentIndex]._DeliveryPlan=this.$refs.receiveList.handleSelection,this.handleSelection=this.tableData[this.currentIndex]._DeliveryPlan;var t="",a=[];this.$refs.receiveList.handleSelection.forEach((function(l){t+=l.order_no+";",e.$set(e.tableData[e.currentIndex],"deliveryPlan",t),a.push(l.id)})),this.tableData[this.currentIndex].dispatch=a||[],this.handleSelection&&0!==this.handleSelection.length||this.$set(this.tableData[this.currentIndex],"deliveryPlan","")},deliverClick:function(e,t){this.material_no_current=e.material_no,this.currentIndex=t,this.handleSelection=this.tableData[this.currentIndex]._DeliveryPlan,this.dialogVisible=!0},equipSelected:function(e,t){this.$set(this.tableData[t],"equip",e)},selectStation:function(e,t){this.$set(this.tableData[t],"station",e?e.name:"")}}},d=u,m=(a("6d7d"),a("2877")),h=Object(m["a"])(d,l,i,!1,null,"7ac80da3",null);t["a"]=h.exports},c740:function(e,t,a){"use strict";var l=a("23e7"),i=a("b727").findIndex,r=a("44d2"),n=a("ae40"),o="findIndex",s=!0,c=n(o);o in[]&&Array(1)[o]((function(){s=!1})),l({target:"Array",proto:!0,forced:s||!c},{findIndex:function(e){return i(this,e,arguments.length>1?arguments[1]:void 0)}}),r(o)}}]);