(window["webpackJsonp"]=window["webpackJsonp"]||[]).push([["chunk-19ad9c2a"],{"0984":function(e,t,a){"use strict";a.d(t,"a",(function(){return l})),a.d(t,"b",(function(){return o})),a.d(t,"c",(function(){return i}));var n=a("b775"),r=a("99b1");function l(e){return Object(n["a"])({url:r["a"].CountSpareInventory,method:"get",params:e})}function o(e){return Object(n["a"])({url:r["a"].SpareInventoryImportExport,method:"get",params:e,responseType:"blob"})}function i(e){return Object(n["a"])({url:r["a"].SpareInventoryImportExport,method:"post",data:e})}},5971:function(e,t,a){"use strict";var n=a("792f"),r=a.n(n);r.a},"67bb":function(e,t,a){"use strict";a.r(t);var n=function(){var e=this,t=e.$createElement,a=e._self._c||t;return a("div",{staticClass:"inventory-manage"},[a("el-form",{attrs:{inline:!0}},[a("el-form-item",{attrs:{label:"物料编码:"}},[a("materialCodeSelect",{attrs:{"is-all-obj":!0,"label-name":"no"},on:{changeSelect:e.changeMaterialCode}})],1),a("el-form-item",{attrs:{label:"物料名称:"}},[a("materialCodeSelect",{attrs:{"is-all-obj":!0},on:{changeSelect:e.changeMaterialName}})],1),a("el-form-item",{attrs:{label:"物料类型:"}},[a("materialTypeSelect",{on:{changeSelect:e.changeMaterialType}})],1)],1),a("el-table",{attrs:{data:e.tableData,border:"","row-class-name":e.tableRowClassName}},[a("el-table-column",{attrs:{type:"index",width:"50",label:"No"}}),a("el-table-column",{attrs:{prop:"type_name",label:"物料类型"}}),a("el-table-column",{attrs:{prop:"spare__no",label:"物料编码"}}),a("el-table-column",{attrs:{prop:"spare__name",label:"物料名称"}}),a("el-table-column",{attrs:{prop:"sum_qty",label:"数量"},scopedSlots:e._u([{key:"default",fn:function(t){return[a("el-link",{attrs:{type:"primary",underline:!1},on:{click:function(a){return e.view(t.row)}}},[e._v(e._s(t.row.sum_qty))])]}}])}),e.checkPermission(["spare_stock","price"])?a("el-table-column",{attrs:{prop:"unit_count",label:"单价（元）"}}):e._e(),a("el-table-column",{attrs:{prop:"unit",label:"单位"}}),e.checkPermission(["spare_stock","price"])?a("el-table-column",{attrs:{prop:"total_count",label:"总价（元）"}}):e._e()],1),a("page",{attrs:{"old-page":!1,total:e.total,"current-page":e.search.page},on:{currentChange:e.currentChange}}),a("el-dialog",{attrs:{title:"备品备件库位库存",visible:e.dialogVisibleResume,width:"90%"},on:{"update:visible":function(t){e.dialogVisibleResume=t}}},[a("locationManage",{attrs:{"is-dialog":!0,show:e.dialogVisibleResume,"dialog-obj":e.dialogObj}})],1)],1)},r=[],l=(a("b0c0"),a("ac1f"),a("841c"),a("96cf"),a("1da1")),o=a("5c1c"),i=a("3e51"),s=a("0984"),c=a("127b"),u=a("a0e0"),p=a("ed08"),b={components:{page:i["a"],materialCodeSelect:o["a"],locationManage:c["default"],materialTypeSelect:u["a"]},data:function(){return{search:{page:1,page_size:10},tableData:[],dialogVisibleResume:!1,dialogObj:{},total:0}},created:function(){this.getList()},methods:{checkPermission:p["a"],getList:function(){var e=this;return Object(l["a"])(regeneratorRuntime.mark((function t(){var a;return regeneratorRuntime.wrap((function(t){while(1)switch(t.prev=t.next){case 0:return t.prev=0,t.next=3,Object(s["a"])(e.search);case 3:a=t.sent,e.tableData=a.results,e.total=a.count,t.next=10;break;case 8:t.prev=8,t.t0=t["catch"](0);case 10:case"end":return t.stop()}}),t,null,[[0,8]])})))()},changeMaterialCode:function(e){this.search.spare_no=e?e.no:null,this.search.page=1,this.getList()},changeMaterialName:function(e){this.search.spare_name=e?e.name:null,this.search.page=1,this.getList()},changeMaterialType:function(e){this.search.type_name=e?e.name:null,this.search.page=1,this.getList()},view:function(e){this.dialogVisibleResume=!0,this.dialogObj=e},tableRowClassName:function(e){var t=e.row;e.rowIndex;return"-"===t.bound?"warning-row":"+"===t.bound?"max-warning-row":""},currentChange:function(e,t){this.search.page=e,this.search.page_size=t,this.getList()}}},m=b,h=(a("5971"),a("2877")),g=Object(h["a"])(m,n,r,!1,null,null,null);t["default"]=g.exports},"792f":function(e,t,a){}}]);