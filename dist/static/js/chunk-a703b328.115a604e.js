(window["webpackJsonp"]=window["webpackJsonp"]||[]).push([["chunk-a703b328"],{"1afa":function(t,e,a){"use strict";a.r(e);var i=function(){var t=this,e=t.$createElement,a=t._self._c||e;return a("div",[a("el-row",[a("el-col",{attrs:{span:12}},[a("el-form",{attrs:{inline:!0}},[a("el-form-item",{staticStyle:{float:"right"}},[a("el-button",{directives:[{name:"permission",rawName:"v-permission",value:["test_type","add"],expression:"['test_type', 'add']"}],on:{click:t.showCreateTestTypeDialog}},[t._v("新建")])],1)],1),a("el-table",{staticStyle:{width:"100%"},attrs:{data:t.tableData,border:"","highlight-current-row":""},on:{"current-change":t.handleTestTypesCurrentRowChange}},[a("el-table-column",{attrs:{align:"center",type:"index",label:"No",width:"50"}}),a("el-table-column",{attrs:{prop:"name",label:"试验类型"}}),a("el-table-column",{attrs:{prop:"test_indicator_name",label:"试验指标"}}),a("el-table-column",{attrs:{label:"操作"},scopedSlots:t._u([{key:"default",fn:function(e){return[a("el-button-group",[a("el-button",{directives:[{name:"permission",rawName:"v-permission",value:["test_type","change"],expression:"['test_type', 'change']"}],attrs:{size:"mini"},on:{click:function(a){return t.showEditTestTypeDialog(e.row)}}},[t._v("编辑")])],1)]}}])})],1),a("page",{attrs:{total:t.total,"current-page":t.getParams.page},on:{currentChange:t.currentChange}})],1),a("el-col",{attrs:{span:12}},[a("el-form",{attrs:{inline:!0}},[a("el-form-item",{staticStyle:{float:"right"}},[a("el-button",{directives:[{name:"permission",rawName:"v-permission",value:["test_type","pointAdd"],expression:"['test_type', 'pointAdd']"}],attrs:{disabled:!t.testTypesCurrentRow},on:{click:t.showCreateDataPointsDialog}},[t._v("新建")])],1)],1),a("el-table",{staticStyle:{width:"100%"},attrs:{data:t.dataPoints,border:""}},[a("el-table-column",{attrs:{label:"No",align:"center",type:"index",width:"50"}}),a("el-table-column",{attrs:{prop:"name",label:"数据点"}}),a("el-table-column",{attrs:{prop:"unit",label:"单位"}}),a("el-table-column",{attrs:{label:"操作"},scopedSlots:t._u([{key:"default",fn:function(e){return[a("el-button-group",[a("el-button",{directives:[{name:"permission",rawName:"v-permission",value:["test_type","pointChange"],expression:"['test_type', 'pointChange']"}],attrs:{size:"mini"},on:{click:function(a){return t.showEditDataPointsDialog(e.row)}}},[t._v("编辑")])],1)]}}])})],1)],1)],1),a("el-dialog",{attrs:{title:"添加试验类型",visible:t.dialogCreateTestTypeVisible,"close-on-click-modal":!1},on:{"update:visible":function(e){t.dialogCreateTestTypeVisible=e}}},[a("el-form",{ref:"createTestTypeForm",attrs:{rules:t.rules,model:t.testTypeForm}},[a("el-form-item",{attrs:{label:"试验类型","label-width":t.formLabelWidth,prop:"name"}},[a("el-input",{model:{value:t.testTypeForm.name,callback:function(e){t.$set(t.testTypeForm,"name",e)},expression:"testTypeForm.name"}})],1),a("el-form-item",{attrs:{label:"试验指标","label-width":t.formLabelWidth,prop:"test_indicator"}},[a("el-select",{attrs:{type:"test_indicator",clearable:"",placeholder:"请选择"},model:{value:t.testTypeForm.test_indicator,callback:function(e){t.$set(t.testTypeForm,"test_indicator",e)},expression:"testTypeForm.test_indicator"}},t._l(t.testIndicatorsOptions,(function(t){return a("el-option",{key:t.id,attrs:{label:t.name,value:t.id}})})),1)],1)],1),a("div",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[a("el-button",{on:{click:function(e){t.dialogCreateTestTypeVisible=!1}}},[t._v("取 消")]),a("el-button",{attrs:{type:"primary"},on:{click:function(e){return t.handleCreateTestType()}}},[t._v("确 定")])],1)],1),a("el-dialog",{attrs:{title:"编辑试验类型",visible:t.dialogEditTestTypeVisible,"close-on-click-modal":!1},on:{"update:visible":function(e){t.dialogEditTestTypeVisible=e}}},[a("el-form",{ref:"editTestTypeForm",attrs:{rules:t.rules,model:t.testTypeForm}},[a("el-form-item",{attrs:{label:"试验类型","label-width":t.formLabelWidth,prop:"name"}},[a("el-input",{model:{value:t.testTypeForm.name,callback:function(e){t.$set(t.testTypeForm,"name",e)},expression:"testTypeForm.name"}})],1),a("el-form-item",{attrs:{label:"试验指标","label-width":t.formLabelWidth,prop:"test_indicator"}},[a("el-select",{attrs:{clearable:"",placeholder:"请选择"},model:{value:t.testTypeForm.test_indicator,callback:function(e){t.$set(t.testTypeForm,"test_indicator",e)},expression:"testTypeForm.test_indicator"}},t._l(t.testIndicatorsOptions,(function(t){return a("el-option",{key:t.id,attrs:{label:t.name,value:t.id}})})),1)],1)],1),a("div",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[a("el-button",{on:{click:function(e){t.dialogEditTestTypeVisible=!1}}},[t._v("取 消")]),a("el-button",{attrs:{type:"primary"},on:{click:t.handleEditTestType}},[t._v("确 定")])],1)],1),a("el-dialog",{attrs:{title:"添加试验",visible:t.dialogCreateDataPointsVisible,"close-on-click-modal":!1},on:{"update:visible":function(e){t.dialogCreateDataPointsVisible=e}}},[a("el-form",{ref:"createDataPointsForm",attrs:{rules:t.rules,model:t.dataPointsForm}},[a("el-form-item",{attrs:{label:"数据点","label-width":t.formLabelWidth,prop:"name"}},[a("el-input",{model:{value:t.dataPointsForm.name,callback:function(e){t.$set(t.dataPointsForm,"name",e)},expression:"dataPointsForm.name"}})],1),a("el-form-item",{attrs:{label:"单位","label-width":t.formLabelWidth,prop:"unit"}},[a("el-input",{model:{value:t.dataPointsForm.unit,callback:function(e){t.$set(t.dataPointsForm,"unit",e)},expression:"dataPointsForm.unit"}})],1)],1),a("div",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[a("el-button",{on:{click:function(e){t.dialogCreateDataPointsVisible=!1}}},[t._v("取 消")]),a("el-button",{attrs:{type:"primary"},on:{click:t.handleCreateDataPoints}},[t._v("确 定")])],1)],1),a("el-dialog",{attrs:{title:"编辑试验",visible:t.dialogEditDataPointsVisible,"close-on-click-modal":!1},on:{"update:visible":function(e){t.dialogEditDataPointsVisible=e}}},[a("el-form",{ref:"editDataPointsForm",attrs:{rules:t.rules,model:t.dataPointsForm}},[a("el-form-item",{attrs:{label:"数据点","label-width":t.formLabelWidth,prop:"name"}},[a("el-input",{model:{value:t.dataPointsForm.name,callback:function(e){t.$set(t.dataPointsForm,"name",e)},expression:"dataPointsForm.name"}})],1),a("el-form-item",{attrs:{label:"单位","label-width":t.formLabelWidth,prop:"unit"}},[a("el-input",{model:{value:t.dataPointsForm.unit,callback:function(e){t.$set(t.dataPointsForm,"unit",e)},expression:"dataPointsForm.unit"}})],1)],1),a("div",{staticClass:"dialog-footer",attrs:{slot:"footer"},slot:"footer"},[a("el-button",{on:{click:function(e){t.dialogEditDataPointsVisible=!1}}},[t._v("取 消")]),a("el-button",{attrs:{type:"primary"},on:{click:t.handleEditDataPoints}},[t._v("确 定")])],1)],1)],1)},o=[],n=(a("b0c0"),a("5530")),s=a("b775"),r=a("99b1");function l(t){return Object(s["a"])({url:r["a"].TestTypes,method:"get",params:t})}function c(t){return Object(s["a"])({url:r["a"].TestTypes,method:"post",data:t})}function d(t,e){return Object(s["a"])({url:r["a"].TestTypes+e+"/",method:"put",data:t})}function u(t){return Object(s["a"])({url:r["a"].TestTypes+t+"/",method:"delete"})}function m(t){return Object(s["a"])({url:r["a"].DataPoints,method:"get",params:t})}function p(t){return Object(s["a"])({url:r["a"].DataPoints,method:"post",data:t})}function f(t,e){return Object(s["a"])({url:r["a"].DataPoints+e+"/",method:"put",data:t})}function h(t){return Object(s["a"])({url:r["a"].DataPoints+t+"/",method:"delete"})}function b(t){return Object(s["a"])({url:r["a"].TestIndicators,method:"get",params:t})}var T=a("3e51"),g=a("2f62"),y={components:{page:T["a"]},data:function(){return{formLabelWidth:"auto",tableData:[],test_indicator:"",testTypesCurrentRow:null,dialogCreateTestTypeVisible:!1,dialogEditTestTypeVisible:!1,testIndicatorsOptions:[],testTypeForm:{name:"",test_indicator:""},rules:{name:[{required:!0,message:"不能为空",trigger:"blur"}],test_indicator:[{required:!0,message:"不能为空",trigger:"blur"}],unit:[{required:!0,message:"不能为空",trigger:"blur"}]},testTypeFormError:{},dataPoints:[],dialogCreateDataPointsVisible:!1,dialogEditDataPointsVisible:!1,dataPointsForm:{name:"",unit:"",test_type:null},dataPointsFormError:{},getParams:{page:1},currentPage:1,total:1}},computed:Object(n["a"])({},Object(g["b"])(["permission"])),created:function(){this.permissionObj=this.permission,this.getTestTypesList()},methods:{afterGetData:function(){this.testTypesCurrentRow=null},getTestTypesList:function(){var t=this;l(this.getParams).then((function(e){t.tableData=e.results,t.total=e.count}))},clearTestTypeForm:function(){this.testTypeForm={name:"",test_indicator:""}},showCreateTestTypeDialog:function(){var t=this;this.clearTestTypeForm(),this.getTestIndicatorsOptions(),this.dialogCreateTestTypeVisible=!0,this.$nextTick((function(){t.$refs.createTestTypeForm.clearValidate()}))},getTestIndicatorsOptions:function(){var t=this;b({all:1}).then((function(e){t.testIndicatorsOptions=e}))},handleCreateTestType:function(){var t=this;this.$refs.createTestTypeForm.validate((function(e){e&&c(t.testTypeForm).then((function(e){t.dialogCreateTestTypeVisible=!1,t.$message(t.testTypeForm.name+"创建成功"),t.currentChange(t.currentPage)}))}))},showEditTestTypeDialog:function(t){var e=this;this.clearTestTypeForm(),this.testTypeForm=Object.assign({},t),this.getTestIndicatorsOptions(),this.dialogEditTestTypeVisible=!0,this.$nextTick((function(){e.$refs.editTestTypeForm.clearValidate()}))},handleEditTestType:function(){var t=this;this.$refs.editTestTypeForm.validate((function(e){e&&d(t.testTypeForm,t.testTypeForm.id).then((function(e){t.dialogEditTestTypeVisible=!1,t.$message(t.testTypeForm.name+"修改成功"),t.currentChange(t.currentPage)}))}))},handleTestTypeDelete:function(t){var e=this;this.$confirm("此操作将永久删除"+t.name+", 是否继续?","提示",{confirmButtonText:"确定",cancelButtonText:"取消",type:"warning"}).then((function(){u(t.id).then((function(t){e.$message({type:"success",message:"删除成功!"}),1===e.tableData.length&&e.currentPage>1&&--e.currentPage,e.currentChange(e.currentPage)}))})).catch((function(){}))},handleTestTypesCurrentRowChange:function(t){var e=this;t&&(this.testTypesCurrentRow=t,m({all:1,test_type_id:t.id}).then((function(a){e.dataPoints=a.results,e.dataPointsForm.test_type=t.id})))},clearDataPointsForm:function(){this.dataPointsForm={name:"",unit:"",description:"",test_type:this.dataPointsForm.test_type}},showCreateDataPointsDialog:function(){var t=this;this.dataPointsForm.test_type&&(this.clearDataPointsForm(),this.dialogCreateDataPointsVisible=!0,this.$nextTick((function(){t.$refs.createDataPointsForm.clearValidate()})))},handleCreateDataPoints:function(){var t=this;this.$refs.createDataPointsForm.validate((function(e){e&&p(t.dataPointsForm).then((function(e){t.dialogCreateDataPointsVisible=!1,t.$message(t.dataPointsForm.name+"创建成功"),t.handleTestTypesCurrentRowChange(t.testTypesCurrentRow)}))}))},showEditDataPointsDialog:function(t){var e=this;this.clearDataPointsForm(),this.dataPointsForm.id=t.id,this.dataPointsForm.name=t.name,this.dataPointsForm.unit=t.unit,this.dialogEditDataPointsVisible=!0,this.$nextTick((function(){e.$refs.editDataPointsForm.clearValidate()}))},handleEditDataPoints:function(){var t=this;this.$refs.editDataPointsForm.validate((function(e){e&&f(t.dataPointsForm,t.dataPointsForm.id).then((function(e){t.dialogEditDataPointsVisible=!1,t.$message(t.dataPointsForm.name+"修改成功"),t.handleTestTypesCurrentRowChange(t.testTypesCurrentRow)}))}))},handleDataPointsDelete:function(t){var e=this;this.$confirm("此操作将永久删除"+t.name+", 是否继续?","提示",{confirmButtonText:"确定",cancelButtonText:"取消",type:"warning"}).then((function(){h(t.id).then((function(t){e.$message({type:"success",message:"删除成功!"}),e.handleTestTypesCurrentRowChange(e.testTypesCurrentRow)})).catch((function(t){e.$message.error(t)}))}))},currentChange:function(t){this.dataPoints=[],this.currentPage=t,this.getParams.page=t,this.getTestTypesList()}}},P=y,F=a("2877"),v=Object(F["a"])(P,i,o,!1,null,"3359eab7",null);e["default"]=v.exports},7156:function(t,e,a){var i=a("861d"),o=a("d2bb");t.exports=function(t,e,a){var n,s;return o&&"function"==typeof(n=e.constructor)&&n!==a&&i(s=n.prototype)&&s!==a.prototype&&o(t,s),t}},a9e3:function(t,e,a){"use strict";var i=a("83ab"),o=a("da84"),n=a("94ca"),s=a("6eeb"),r=a("5135"),l=a("c6b6"),c=a("7156"),d=a("c04e"),u=a("d039"),m=a("7c73"),p=a("241c").f,f=a("06cf").f,h=a("9bf2").f,b=a("58a8").trim,T="Number",g=o[T],y=g.prototype,P=l(m(y))==T,F=function(t){var e,a,i,o,n,s,r,l,c=d(t,!1);if("string"==typeof c&&c.length>2)if(c=b(c),e=c.charCodeAt(0),43===e||45===e){if(a=c.charCodeAt(2),88===a||120===a)return NaN}else if(48===e){switch(c.charCodeAt(1)){case 66:case 98:i=2,o=49;break;case 79:case 111:i=8,o=55;break;default:return+c}for(n=c.slice(2),s=n.length,r=0;r<s;r++)if(l=n.charCodeAt(r),l<48||l>o)return NaN;return parseInt(n,i)}return+c};if(n(T,!g(" 0o1")||!g("0b1")||g("+0x1"))){for(var v,_=function(t){var e=arguments.length<1?0:t,a=this;return a instanceof _&&(P?u((function(){y.valueOf.call(a)})):l(a)!=T)?c(new g(F(e)),a,_):F(e)},C=i?p(g):"MAX_VALUE,MIN_VALUE,NaN,NEGATIVE_INFINITY,POSITIVE_INFINITY,EPSILON,isFinite,isInteger,isNaN,isSafeInteger,MAX_SAFE_INTEGER,MIN_SAFE_INTEGER,parseFloat,parseInt,isInteger".split(","),w=0;C.length>w;w++)r(g,v=C[w])&&!r(_,v)&&h(_,v,f(g,v));_.prototype=y,y.constructor=_,s(o,T,_)}}}]);