;(function () {

    var Main = {
        mixins: [BaseMixin, Rubber_Material_filter],
        data: function () {

            return {
                currentPage:1,
                pageSize:null,
                tableDataTotal:null,
                currentRow: {
                    used_type: -1
                },
                raw_material_currentRow:{},
                tableDataUrl: RubberMaterialUrl,
                tableRawMaterialData: [],
                RubberState: "",
                RubberStateOptions: [],
                RubberSite: "",
                RubberSiteOptions: [],
                RubberStage: "",
                RubberStageOptions: [],
                factory:"",
                PopupRubberSITEOptions:[],
                stage_product_batch_no:"",
                ProductBatchNoOptions:[],
                stage:"",
                StageOptions:[],
                dev_type_name: "",
                DevTypeOptions: [],
                RawMaterialOptions: [],
                NewRowMaterial:[{
                    sn_ele:null,
                    material_type:null,
                    material_name:null,
                    practical_weight:null}
                ],
                PutProductRecipe:[{
                    sn:null,
                    material_type:null,
                    material_name:null,
                    actual_weight:null}
                ],

                PopupRubberSITE:[],
                DevType:[],
                ProductBatchNo:[],
                Stage:[],
                generate_material_no:"",
                //反炼与否和时间
                select_rm_flag:false,
                select_rm_time_interval:"",

                select_stage_product_batch_no:null,
                select_product_name:null,
                select_status:null,
                select_dev_type:null,
                select_material_weight:null,
                select_material_volume:null,
                select_rubber_proportion:null,

                ratioSum:null,
                ratioVolumeSum:null,
                calculateVolumeSum:null,
                calculateWeightSum:null,
                practicalWeightSum:null,
                practicalVolumeSum:null,


                pre_ratioVolume:null,
                pre_calculateVolume:null,
                pre_calculateWeight:null,
                pre_practical_weight:null,
                pre_practicalVolumeSum:null,
                //配料更新时: 变量
                put_select_stage_product_batch_no:null,
                put_select_product_name:null,
                put_select_status:null,
                put_select_dev_type:null,
                put_select_material_weight:null,
                put_select_material_volume:null,
                put_select_rubber_proportion:null,
                put_select_rm_flag:null,
                put_select_rm_time_interval:null,
                put_discharge_time_material:null,

                put_ratioSum:null,
                put_ratioVolumeSum:null,
                put_calculateVolumeSum:null,
                put_calculateWeightSum:null,
                put_practicalWeightSum:null,
                put_practicalVolumeSum:null,


                selectedPreMaterials:[],
                ProductRecipe:[],
                pre_time_material:"",
                time_material:"",
                //排出行对应的时间---炼胶时间
                discharge_time_material:"",


                dialogAddRubberMaterial: false,
                dialogRubberMaterialStandard:false,
                dialogChoiceMaterials:false,
                NewdialogChoiceMaterials:false,
                dialogRawMaterialSync:false,
                sn:null,
                material:null,
                material_type:null,
                material_name:null,
                material_type_name:null,

                rubberMaterialForm: {
                    factory: "",
                    stage_product_batch_no: "",
                    stage: "",
                    dev_type_name: "",
                },
                rules: {
                    factory: [{ required: true, message: '请选择产地', trigger: 'change' }],
                    SITE: [{ required: true, message: '请选择SITE', trigger: 'change' }],
                    rubber_no: [{ required: true, message: '请选择胶料编码', trigger: 'change' }],
                    stage: [{ required: true, message: '请选择段次', trigger: 'change' }],
                    version: [{ required: true, message: '请选择版本', trigger: 'blur' }],
                },
                rubberMaterialFormError: {
                    factory: "",
                    SITE: "",
                    rubber_no: "",
                    stage: "",
                    version: "",
                },
                pop_up_raw_material_type:"",
                pop_up_raw_material_no:"",
                pop_up_raw_material_name:"",
                raw_material_index:null,
                put_raw_material_index:null,
            }
        },
        created: function () {

            var app = this;
            axios.get(StateGlobalUrl, {
            }).then(function (response) {
                app.RubberStateOptions = response.data.results;
            }).catch(function (error) {
            });

            axios.get(SiteGlobalUrl, {
            }).then(function (response) {
                app.RubberSiteOptions = response.data.results;
            }).catch(function (error) {
            });

            axios.get(StageGlobalUrl, {
            }).then(function (response) {
                app.RubberStageOptions = response.data.results;
            }).catch(function (error) {
            });

            axios.get(SITEGlobalUrl, {
            }).then(function (response) {
                app.PopupRubberSITEOptions = response.data.results;
            }).catch(function (error) {
            });
            axios.get(ProductInfosUrl + '?all=1', {
            }).then(function (response) {
                app.ProductBatchNoOptions = response.data.results;
            }).catch(function (error) {
            });


            axios.get(DevTypeGlobalUrl, {
            }).then(function (response) {
                app.DevTypeOptions = response.data.results;
            }).catch(function (error) {
            });
            app.get_raw_material()



        },
        methods: {
            get_raw_material(val=1){
                var app=this;
                 axios.get(MaterialsUrl + '?page=' + val, {
                }).then(function (response) {
                    app.RawMaterialOptions = response.data.results;
                    app.tableRawMaterialData = response.data.results;
                    app.tableDataTotal = response.data.count;
                }).catch(function (error) {
                });
            },
            usedTypeFormatter: function (row, column) {

                return this.usedTypeChoice(row.used_type);
            },
            usedTypeChoice: function (usedType) {

                switch (usedType) {

                    case 1:
                        return "编辑";
                    case 2:
                        return "通过";
                    case 3:
                        return "应用";
                    case 4:
                        return "驳回";
                    case 5:
                        return "废弃";
                }
            },

            formatter: function (row, column) {

                return row.rm_flag ? "Y" : "N"
            },
            beforeGetData() {
                this.getParams["used_type"] = this.RubberState;
                this.getParams["factory_id"] = this.RubberSite;
                this.getParams["stage_id"] = this.RubberStage;
                this.getParams['stage_product_batch_no'] = this.stage_product_batch_no;
            },
            RubberStateChange: function () {

                this.getFirstPage();
            },
            RubberSiteChange: function () {

                this.getFirstPage();
            },
            RubberStageChange: function () {

                this.getFirstPage();
            },

            shiftsStageChange(){

            },

            shiftsDevTypeChange() {
            },

            rubber_no_querySearchAsync(queryString, cb) {
                var app = this;
                var search_rubber_no = app.ProductBatchNoOptions;

                var results = queryString ? search_rubber_no.filter(this.rubber_no_createFilter(queryString)) : search_rubber_no;
                // 调用 callback 返回建议列表的数据
                cb(results);
            },
            rubber_no_createFilter(queryString) {
                return (search_rubber_no) => {
                  return (search_rubber_no.product_name.toLowerCase().indexOf(queryString.toLowerCase()) === 0);
                };
            },

            GenerateRubberMaterialNOChanged() {
                var app = this;
                var SITE_name = "";
                var stage_name = "";
                var product_name = "";
                if(app.rubberMaterialForm.SITE){
                    for(var i=0; i<app.PopupRubberSITEOptions.length; ++i){
                        if(app.PopupRubberSITEOptions[i]["id"] == app.rubberMaterialForm.SITE){
                              SITE_name = app.PopupRubberSITEOptions[i]['global_name']
                          }
                    }
                }
                if(app.rubberMaterialForm.stage){
                    for(var j=0; j<app.RubberStageOptions.length; ++j){
                        if(app.RubberStageOptions[j]["id"] == app.rubberMaterialForm.stage){
                              stage_name = app.RubberStageOptions[j]['global_name']
                          }
                    }
                }
                if(app.rubberMaterialForm.rubber_no){
                    product_name = app.rubberMaterialForm.rubber_no
                }

                app.rubberMaterialForm.generate_material_no = SITE_name + '-' + stage_name +'-'+ product_name+'-' + app.rubberMaterialForm.version;
            },

            showAddRubberMaterialDialog: function () {
                this.rubberMatetialError = "";
                this.rubberMaterialForm = {
                    factory: "",
                    stage_product_batch_no: "",
                    stage: "",
                    dev_type_name: "",
                };
                this.dialogAddRubberMaterial = true;
                this.currentRow = {
                    used_type: -1
                } // 新建和更新标志 -1新建 其他更新
            },
            showPutRubberMaterialDialog: function() {
                var app = this;
                app.dialogRubberMaterialStandard = true;
                axios.get(RubberMaterialUrl + this.currentRow.id + "/")
                    .then(function (response) {
                        console.log('================================mod_get');
                        console.log(response.data.batching_details);
                        console.log('================================mod_get');
                        app.put_select_stage_product_batch_no = response.data['stage_product_batch_no'];
                        app.put_select_product_name = response.data['product_name'];
                        app.put_select_status = app.usedTypeChoice(response.data['used_type']);
                        app.put_select_dev_type = response.data['dev_type_name'];

                        app.put_select_material_weight = response.data['batching_weight'];
                        app.put_select_rm_time_interval = response.data['production_time_interval'];
                        if(response.data.batching_details.length ==0){
                            app.PutProductRecipe = [{
                                sn:null,
                                material_type:null,
                                material_name:null,
                                actual_weight:null}]
                        }else{
                            app.PutProductRecipe = response.data.batching_details;
                        }

                    }).catch(function (error) {

                });

            },


            NewhandleAddRubberMaterial(formName) {
                var app = this;
                app.$refs[formName].validate((valid) => {
                  if (valid) {
                      console.log('=============================');
                      console.log(app.rubberMaterialForm['rubber_no']);
                      console.log('=============================');
                      var v_product_info = "";
                      //判断表格中每一行中的下拉框中的数据：是用户所选，还是默认展示
                        for(var j = 0; j < app.ProductBatchNoOptions.length; ++j){
                            if(app.ProductBatchNoOptions[j]['product_name'] == app.rubberMaterialForm['rubber_no']){
                                v_product_info = app.ProductBatchNoOptions[j]['id'];
                                break
                            }
                        }
                        console.log('=============================');
                      console.log(v_product_info);
                      console.log('=============================');
                      axios.post(RubberMaterialUrl, {
                            factory: app.rubberMaterialForm['factory'],
                            site: app.rubberMaterialForm['SITE'],
                            product_info: v_product_info,
                            precept: app.rubberMaterialForm['scheme'],
                            stage_product_batch_no: app.rubberMaterialForm['generate_material_no'],
                            stage: app.rubberMaterialForm['stage'],
                            versions: app.rubberMaterialForm['version'],
                        }).then(function (response) {

                            app.dialogAddRubberMaterial = false;
                            app.$message(app.rubberMaterialForm['generate_material_no'] + "保存成功");
                            app.currentChange(app.currentPage);

                        }).catch(function (error) {
                            app.$message({
                                message: error.response.data,
                                type: 'error'
                            });
                        });

                  } else {
                    console.log('error submit!!');
                    return false;
                  }
                });


            },

            NewAddMaterial(formName) {
                var app = this;
                app.$refs[formName].validate((valid) => {
                  if (valid) {
                        app.dialogAddRubberMaterial = false;
                        app.NewdialogChoiceMaterials = true;
                        app.select_stage_product_batch_no = app.rubberMaterialForm['generate_material_no'];
                        app.select_product_name = app.rubberMaterialForm['rubber_no'];
                        app.select_material_weight = null;
                        app.practicalWeightSum = null;
                        app.NewRowMaterial = [];
                  } else {
                    console.log('error submit!!');
                    return false;
                  }
                });
            },


            NewMaterialChange: function(row) {
                var app = this;
                for(var i=0; i<app.RawMaterialOptions.length; ++i){
                    if(app.RawMaterialOptions[i]["id"] == row.material_name){
                          // row.sn_ele = app.NewRowMaterial.length;
                          row.material_type = app.RawMaterialOptions[i]['material_type_name']
                      }
                }
            },
            PutNewMaterialChange: function(row) {
                var app = this;
                for(var i=0; i<app.RawMaterialOptions.length; ++i){
                    if(app.RawMaterialOptions[i]["id"] == row.material_name){
                          // row.sn = app.PutProductRecipe.length;
                          row.material_type = app.RawMaterialOptions[i]['material_type_name']
                      }
                }
            },

            NewPracticalWeightChanged: function () {
                var app = this;

                var material_weight = 0;
                for(var i=0; i<app.NewRowMaterial.length; ++i){
                    material_weight += app.NewRowMaterial[i]['practical_weight']
                }
                app.select_material_weight = material_weight;
                app.practicalWeightSum = material_weight;
            },
            insert_NewPracticalWeightChanged: function() {
                this.NewRowMaterial.push({
                    sn:"",
                    material_type:"",
                    material_name:"",
                    practical_weight:""
                });
            },
            PutNewPracticalWeightChanged: function () {
                var app = this;

                var material_weight = 0;
                for(var i=0; i<app.PutProductRecipe.length; ++i){
                    material_weight += app.PutProductRecipe[i]['actual_weight']
                }
                app.put_select_material_weight = material_weight;
                app.put_practicalWeightSum = material_weight;
            },
            insert_PutNewPracticalWeightChanged: function() {
                this.PutProductRecipe.push({
                    sn:"",
                    material_type:"",
                    material_name:"",
                    actual_weight:""
                });
            },

            NewsaveMaterialClicked: function () {
                var app = this;
                var batching_details_list = [];
                var post_ele_material = "";

                for (var i = 0; i < this.NewRowMaterial.length -1; ++i) {
                    if(app.NewRowMaterial[i].material_name && app.NewRowMaterial[i].practical_weight){
                        // post_ele_material = app.NewRowMaterial[i].material_name;
                        //判断表格中每一行中的下拉框中的数据：是用户所选，还是默认展示
                        for(var j = 0; j < app.RawMaterialOptions.length; ++j){
                            if(app.RawMaterialOptions[j]['material_name'] == app.NewRowMaterial[i].material_name){
                                post_ele_material = app.RawMaterialOptions[j]['id'];
                                break
                            }
                        }
                        console.log('============================================');
                        console.log(app.NewRowMaterial[i].material);
                        console.log('============================================');
                        var now_stage_material = {
                            sn: i+1,
                            material:app.NewRowMaterial[i].material,
                            actual_weight:app.NewRowMaterial[i].practical_weight,
                        };
                        batching_details_list.push(now_stage_material);
                    }
                    else {
                        app.$message({
                            message: "必填数据不能为空",
                            type: 'error'
                        });
                        return
                    }
                }
                var v_product_info = "";
                  //判断表格中每一行中的下拉框中的数据：是用户所选，还是默认展示
                for(var j = 0; j < app.ProductBatchNoOptions.length; ++j){
                    if(app.ProductBatchNoOptions[j]['product_name'] == app.rubberMaterialForm['rubber_no']){
                        v_product_info = app.ProductBatchNoOptions[j]['id'];
                        break
                    }
                }
                axios.post(RubberMaterialUrl, {
                    factory: app.rubberMaterialForm['factory'],
                    site: app.rubberMaterialForm['SITE'],
                    product_info: v_product_info,
                    precept: app.rubberMaterialForm['scheme'],
                    stage_product_batch_no: app.rubberMaterialForm['generate_material_no'],
                    stage: app.rubberMaterialForm['stage'],
                    versions: app.rubberMaterialForm['version'],
                    batching_details: batching_details_list,
                }).then(function (response) {

                    app.NewdialogChoiceMaterials = false;
                    app.$message(app.rubberMaterialForm['generate_material_no'] + "保存成功");
                    app.currentChange(app.currentPage);

                }).catch(function (error) {
                    app.$message({
                        message: error.response.data,
                        type: 'error'
                    });
                });

            },

            PutNewsaveMaterialClicked: function () {
                var app = this;
                var batching_details_list = [];
                //循环整个表格
                for (var i = 0; i < this.PutProductRecipe.length; ++i) {
                    //只有原材料和实际重量两个必选项都填写时，才能往batching_details_list中push
                    if(app.PutProductRecipe[i].material_name && app.PutProductRecipe[i].actual_weight){

                        var now_stage_material = {
                            sn: i+1,
                            material:app.PutProductRecipe[i].material,
                            actual_weight:app.PutProductRecipe[i].actual_weight,
                        };
                        batching_details_list.push(now_stage_material);

                    }
                    else {
                    }
                }



                console.log('=======================================mod_put');
                console.log(batching_details_list);
                console.log('=======================================mod_put    ');
                axios.put(RubberMaterialUrl + this.currentRow.id + "/", {
                    dev_type: app.put_select_dev_type,
                    production_time_interval: app.put_select_rm_time_interval,
                    batching_details: batching_details_list,
                }).then(function (response) {

                    app.dialogRubberMaterialStandard = false;
                    app.$message(app.put_select_stage_product_batch_no + "保存成功");
                    app.currentChange(app.currentPage);

                }).catch(function (error) {
                    app.$message({
                        message: error.response.data,
                        type: 'error'
                    });
                });

            },

            pop_up_raw_material: function(new_material_ele, index){
                var app = this;
                if(new_material_ele.hasOwnProperty("practical_weight")){
                    app.raw_material_index = index;
                }else {
                    app.put_raw_material_index = index;
                }

                app.dialogRawMaterialSync = true;
            },

            afterGetData: function () {

                this.currentRow = {
                    used_type: -1
                }
            },

            RmFlagFormatter: function(row, column) {

                return this.boolFormatter(row.rm_flag);
            },

            handleMaterialSelect(row) {
                var app = this;
                //胶料配料post
                if(app.raw_material_index != null){
                    app.NewRowMaterial[app.raw_material_index].material_name = row.material_name;
                    app.NewRowMaterial[app.raw_material_index].material = row.id;
                    app.NewRowMaterial[app.raw_material_index].material_type = row.material_type_name;
                }else {
                    //胶料配料put
                    app.PutProductRecipe[app.put_raw_material_index].material_name = row.material_name;
                    app.PutProductRecipe[app.put_raw_material_index].material = row.id;
                    app.PutProductRecipe[app.put_raw_material_index].material_type = row.material_type_name;
                }
                app.dialogRawMaterialSync = false;
            },
            handleCurrentChange: function (val) {

                this.currentRow = val;
            },
            raw_material_handleCurrentChange: function (val) {
                this.raw_material_currentRow = val;
                this.get_raw_material(val)
            },

        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount('#app')
})();
