;(function () {

    var Main = {
        mixins: [BaseMixin, Rubber_Material_filter],
        data: function () {

            return {
                currentRow: {
                    used_type: -1
                },
                tableDataUrl: RubberMaterialUrl,
                RubberState: "",
                RubberStateOptions: [],
                RubberSite: "",
                RubberSiteOptions: [],
                RubberStage: "",
                RubberStageOptions: [],
                factory:"",
                PopupRubberSiteOptions:[],
                stage_product_batch_no:"",
                ProductBatchNoOptions:[],
                stage:"",
                StageOptions:[],
                dev_type_name: "",
                DevTypeOptions: [],

                PopupRubberSite:[],
                DevType:[],
                ProductBatchNo:[],
                Stage:[],
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
                PutProductRecipe:[],
                pre_time_material:"",
                time_material:"",
                //排出行对应的时间---炼胶时间
                discharge_time_material:"",


                dialogAddRubberMaterial: false,
                dialogRubberMaterialStandard:false,
                dialogChoiceMaterials:false,

                rubberMaterialForm: {
                    factory: "",
                    stage_product_batch_no: "",
                    stage: "",
                    dev_type_name: "",
                },
                rules: {
                    factory: [{ required: true, message: '请选择产地', trigger: 'change' }],
                    stage_product_batch_no: [{ required: true, message: '请选择胶料编码', trigger: 'change' }],
                    stage: [{ required: true, message: '请选择段次', trigger: 'change' }],
                    dev_type_name: [{ required: true, message: '请选择炼胶机类型', trigger: 'change' }],
                },
                rubberMaterialFormError: {
                    factory: "",
                    stage_product_batch_no: "",
                    stage: "",
                    dev_type_name: "",
                }
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

            axios.get(SiteGlobalUrl, {
            }).then(function (response) {
                app.PopupRubberSite = response.data.results;
                    for (var i = 0; i < app.PopupRubberSite.length; ++i) {
                        app.PopupRubberSiteOptions.push({
                            value: app.PopupRubberSite[i]["id"],
                            label: app.PopupRubberSite[i]["global_name"],
                        });
                    }
            }).catch(function (error) {
            });

            axios.get(DevTypeGlobalUrl, {
            }).then(function (response) {
                app.DevType = response.data.results;
                    for (var i = 0; i < app.DevType.length; ++i) {
                        var label = app.DevType[i]["global_name"];
                        app.DevTypeOptions.push({
                            value: app.DevType[i]["id"],
                            label
                        });
                    }
            }).catch(function (error) {
            });


        },
        methods: {
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
            shiftsPopupRubberSiteChange(){
                var app = this;
                axios.get(RubberStageUrl + '?factory_id=' +this.rubberMaterialForm['factory'], {}
                ).then(function (response) {
                    app.ProductBatchNo = response.data;
                        for (var i = 0; i < app.ProductBatchNo.length; ++i) {
                            app.ProductBatchNoOptions.push({
                                value: app.ProductBatchNo[i]["product_info"],
                                label: app.ProductBatchNo[i]["product_no"],
                            });
                        }
                }).catch(function (error) {
                });
            },
            shiftsProductBatchNoChange(){
                var app = this;
                axios.get(RubberStageUrl + '?factory_id=' + this.rubberMaterialForm['factory'], {}
                ).then(function (response) {
                    app.Stage = response.data;
                    for (var i = 0; i < app.Stage.length; ++i) {
                        if(app.Stage[i]["product_info"] == app.rubberMaterialForm['stage_product_batch_no']){
                            for(var j = 0; j < app.Stage[i]['stages'].length; ++j){
                                app.StageOptions.push({
                                    value: app.Stage[i]['stages'][j]["stage"],
                                    label: app.Stage[i]['stages'][j]["stage__global_name"],
                                });
                            }
                        }
                    }
                }).catch(function (error) {
                });
            },

            shiftsStageChange(){

            },

            shiftsDevTypeChange() {
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
                        app.put_select_stage_product_batch_no = response.data['stage_product_batch_no'];
                        app.put_select_product_name = response.data['product_name'];
                        // app.put_select_status = response.data['used_type'];
                        app.put_select_status = app.usedTypeChoice(response.data['used_type']);
                        app.put_select_dev_type = response.data['dev_type_name'];
                        app.put_select_material_weight = response.data['batching_weight'];
                        app.put_select_material_volume = response.data['volume'];
                        app.put_select_rubber_proportion = response.data['batching_proportion'];
                        app.put_select_rm_flag = response.data['rm_flag'];
                        app.put_select_rm_time_interval = response.data['rm_time_interval'];
                        app.PutProductRecipe = response.data.batching_details;
                        app.put_discharge_time_material = response.data['production_time_interval'];

                    }).catch(function (error) {

                });

            },
            PutPracticalWeightChanged: function(){
                var variate_ratio = 0;
                var variate_ratioVolume = 0;
                var variate_practical_weight = 0;
                var variate_practical_volume = 0;
                var variate_calculateWeight = 0;

                for (var i = 0; i < this.PutProductRecipe.length; ++i) {
                    //配比体积的计算
                    this.PutProductRecipe[i].ratio_weight = Number(this.PutProductRecipe[i].ratio / this.PutProductRecipe[i].density);
                    //实际体积的计算
                    this.PutProductRecipe[i].actual_volume = Number(this.PutProductRecipe[i].actual_weight / this.PutProductRecipe[i].density);
                    variate_ratio += Number(this.PutProductRecipe[i].ratio);
                    variate_ratioVolume += Number(this.PutProductRecipe[i].ratio_weight);
                    variate_practical_weight += Number(this.PutProductRecipe[i].actual_weight);
                    variate_practical_volume += Number(this.PutProductRecipe[i].actual_volume)
                }
                this.put_ratioSum = variate_ratio;
                this.put_ratioVolumeSum = variate_ratioVolume;
                this.put_calculateVolumeSum = this.put_select_dev_type;
                this.put_practicalWeightSum = variate_practical_weight;
                this.put_practicalVolumeSum = variate_practical_volume;
                //标题栏中的：配料重量、配料体积、胶料比重
                this.put_select_material_weight = variate_practical_weight;
                this.put_select_material_volume = variate_practical_volume;
                this.put_select_rubber_proportion = Number(this.put_practicalWeightSum / this.put_practicalVolumeSum).toFixed(2);
                //以下针对'本段次' xxx(计算体积)、xxx(计算重量)、 的计算
                for (var j = 0; j < this.PutProductRecipe.length; ++j) {
                    //计算体积的计算
                    this.PutProductRecipe[j].standard_volume = Number(this.put_select_dev_type / (this.put_ratioVolumeSum / this.PutProductRecipe[j].ratio_weight)).toFixed(2);
                    //计算重量的计算
                    this.PutProductRecipe[j].standard_weight = Number(this.PutProductRecipe[j].density * this.PutProductRecipe[j].standard_volume).toFixed(2);
                    variate_calculateWeight += Number(this.PutProductRecipe[j].standard_weight);
                }

                this.put_calculateWeightSum = variate_calculateWeight;

            },

            handleAddRubberMaterial(formName) {
                var app = this;
                app.$refs[formName].validate((valid) => {
                  if (valid) {
                      //胶料配料标准要显示的标题------------------------------------------------------------------------开始
                      //以下用于拼接胶料配料的编号：格式：产地-胶料编码-段次-版本 ----------开始
                      for(var i = 0; i < app.PopupRubberSite.length; ++i){
                          if(app.PopupRubberSite[i]["id"] == app.rubberMaterialForm['factory']){
                              var chandi_no = app.PopupRubberSite[i]['global_no']
                          }
                      }
                      for(var j = 0; j < app.ProductBatchNo.length; ++j){
                          if(app.ProductBatchNo[j]["product_info"] == app.rubberMaterialForm['stage_product_batch_no']){
                              var jiaoliao_no  = app.ProductBatchNo[j]['product_no'];
                              var jiaoliao_id  = app.ProductBatchNo[j]['product_info'];
                              var jiaoliao_name  = app.ProductBatchNo[j]['product_name'];
                              var peiliao_status = app.ProductBatchNo[j]['used_type'];
                          }
                      }
                      for(var k = 0; k < app.Stage.length; ++k){
                          if(app.Stage[k]["product_info"] == app.rubberMaterialForm['stage_product_batch_no']){
                              for(var m = 0; m < app.Stage[k]['stages'].length; ++m){
                                  if(app.Stage[k]["stages"][m]['stage'] == app.rubberMaterialForm['stage']){
                                      var duanci_no = app.Stage[k]["stages"][m]['stage__global_name']
                                  }
                              }
                          }
                      }
                      for(var n = 0; n < app.ProductBatchNo.length; ++n){
                          if(app.ProductBatchNo[n]["product_info"] == app.rubberMaterialForm['stage_product_batch_no']){
                              var version  = app.ProductBatchNo[n]['versions']
                          }
                      }
                      app.select_stage_product_batch_no = chandi_no+'-'+jiaoliao_no+'-'+duanci_no+'-'+version;
                      //以下用于拼接胶料配料的编号：格式：产地-胶料编码-段次-版本 ----------结束
                      app.select_product_name = jiaoliao_name;
                      app.select_status = peiliao_status;
                      for(var p = 0; p < app.DevType.length; ++p){
                          if(app.DevType[p]["id"] == app.rubberMaterialForm['dev_type_name']){
                              var dev_type = app.DevType[p]['global_name']
                          }
                      }
                      app.select_dev_type = dev_type;
                      //胶料配料标准要显示的标题------------------------------------------------------------------------结束
                      //当前选择的 配方和段次 是否有上段次的信息
                      axios.get(PreBatchInfoUrl + '?product_info_id='+jiaoliao_id+'&stage_id='+app.rubberMaterialForm['stage'], {}
                      ).then(function (response) {
                            app.selectedPreMaterials = response.data;

                            app.rubberMatetialError = "";
                            app.dialogAddRubberMaterial = false;
                            app.dialogChoiceMaterials = true;
                      }).catch(function (error) {
                          app.$message({
                                message: error.response.data,
                                type: 'error'
                            });
                      });
                      //当前选择的 配方和段次 对应的原料信息（为该配方对应的段次 添加配料）
                      axios.get(ProductRecipeUrl + '?product_info_id='+jiaoliao_id+'&stage_id='+app.rubberMaterialForm['stage'], {}
                      ).then(function (response) {
                          app.ProductRecipe = response.data;
                      }).catch(function (error) {
                          app.dialogAddRubberMaterial = true;
                          app.dialogChoiceMaterials = false;

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

            //胶料配料标准 本段 的数据
            PracticalWeightChanged: function () {
                var variate_ratio = 0;
                var variate_ratioVolume = 0;
                var variate_practical_weight = 0;
                var variate_practical_volume = 0;
                var variate_calculateWeight = 0;
                if(this.selectedPreMaterials.material_type){
                    console.log('==============================');
                    console.log('上段次存在');
                    console.log('==============================');
                    //'上段次'配比体积的计算
                    this.selectedPreMaterials.pre_ratioVolume = Number(Number(this.selectedPreMaterials.ratio) / Number(this.selectedPreMaterials.density));
                    //'上段次'实际体积的计算
                    this.selectedPreMaterials.pre_practicalVolume = Number(this.selectedPreMaterials.pre_practical_weight / this.selectedPreMaterials.density);

                    //以下针对配比、比重、配比体积、xxx(计算体积)、xxx(计算重量)、实际重量、实际体积 的计算

                    for (var i = 0; i < this.ProductRecipe.length; ++i) {
                        //配比体积的计算
                        this.ProductRecipe[i].ratioVolume = Number(this.ProductRecipe[i].ratio / this.ProductRecipe[i].density);
                        //实际体积的计算
                        this.ProductRecipe[i].practicalVolume = Number(this.ProductRecipe[i].practical_weight / this.ProductRecipe[i].density);
                        variate_ratio += Number(this.ProductRecipe[i].ratio);
                        variate_ratioVolume += this.ProductRecipe[i].ratioVolume;
                        variate_practical_weight += this.ProductRecipe[i].practical_weight;
                        variate_practical_volume += this.ProductRecipe[i].practicalVolume
                    }
                    this.ratioSum = variate_ratio + this.selectedPreMaterials.ratio;
                    this.ratioVolumeSum = variate_ratioVolume + this.selectedPreMaterials.pre_ratioVolume;
                    this.calculateVolumeSum = this.select_dev_type;
                    this.practicalWeightSum = variate_practical_weight + this.selectedPreMaterials.pre_practical_weight;
                    this.practicalVolumeSum = variate_practical_volume + this.selectedPreMaterials.pre_practicalVolume;
                    //标题栏中的：配料重量、配料体积、胶料比重
                    this.select_material_weight = variate_practical_weight + this.selectedPreMaterials.pre_practical_weight;
                    this.select_material_volume = variate_practical_volume + this.selectedPreMaterials.pre_practicalVolume;
                    this.select_rubber_proportion = Number(this.practicalWeightSum / this.practicalVolumeSum).toFixed(2);
                    //以下针对'本段次' xxx(计算体积)、xxx(计算重量)、 的计算

                    for (var j = 0; j < this.ProductRecipe.length; ++j) {
                        //计算体积的计算
                        this.ProductRecipe[j].calculateVolume = Number(this.select_dev_type / (this.ratioVolumeSum / this.ProductRecipe[j].ratioVolume)).toFixed(2);
                        //计算重量的计算
                        this.ProductRecipe[j].calculateWeight = Number(this.ProductRecipe[j].density * this.ProductRecipe[j].calculateVolume).toFixed(2);
                        variate_calculateWeight += Number(this.ProductRecipe[j].calculateWeight);
                    }
                    //以下针对'上段次' xxx(计算体积)、xxx(计算重量)、 的计算
                    this.selectedPreMaterials.pre_calculateVolume = Number(this.select_dev_type / (this.ratioVolumeSum / this.selectedPreMaterials.pre_ratioVolume)).toFixed(2);
                    this.selectedPreMaterials.pre_calculateWeight = Number(this.selectedPreMaterials.density * this.selectedPreMaterials.pre_calculateVolume).toFixed(2);

                    this.calculateWeightSum = variate_calculateWeight + Number(this.selectedPreMaterials.pre_calculateWeight);
                }
                else{
                    console.log('==============================');
                    console.log('上段次不存在');
                    console.log('==============================');
                    //以下针对配比、比重、配比体积、xxx(计算体积)、xxx(计算重量)、实际重量、实际体积 的计算
                    for (var i = 0; i < this.ProductRecipe.length; ++i) {
                        //配比体积的计算
                        this.ProductRecipe[i].ratioVolume = Number(this.ProductRecipe[i].ratio / this.ProductRecipe[i].density);
                        //实际体积的计算
                        this.ProductRecipe[i].practicalVolume = Number(this.ProductRecipe[i].practical_weight / this.ProductRecipe[i].density);
                        variate_ratio += Number(this.ProductRecipe[i].ratio);
                        variate_ratioVolume += this.ProductRecipe[i].ratioVolume;
                        variate_practical_weight += this.ProductRecipe[i].practical_weight;
                        variate_practical_volume += this.ProductRecipe[i].practicalVolume
                    }
                    this.ratioSum = variate_ratio;
                    this.ratioVolumeSum = variate_ratioVolume;
                    this.calculateVolumeSum = this.select_dev_type;
                    this.practicalWeightSum = variate_practical_weight;
                    this.practicalVolumeSum = variate_practical_volume;
                    //标题栏中的：配料重量、配料体积、胶料比重
                    this.select_material_weight = variate_practical_weight;
                    this.select_material_volume = variate_practical_volume;
                    this.select_rubber_proportion = Number(this.practicalWeightSum / this.practicalVolumeSum).toFixed(2);
                    //以下针对'本段次' xxx(计算体积)、xxx(计算重量)、 的计算
                    for (var j = 0; j < this.ProductRecipe.length; ++j) {
                        //计算体积的计算
                        this.ProductRecipe[j].calculateVolume = Number(this.select_dev_type / (this.ratioVolumeSum / this.ProductRecipe[j].ratioVolume)).toFixed(2);
                        //计算重量的计算
                        this.ProductRecipe[j].calculateWeight = Number(this.ProductRecipe[j].density * this.ProductRecipe[j].calculateVolume).toFixed(2);
                        variate_calculateWeight += Number(this.ProductRecipe[j].calculateWeight);
                    }

                    this.calculateWeightSum = variate_calculateWeight;
                }
            },

            saveMaterialClicked: function () {
                var app = this;
                var batching_details_list = [];
                var variate_num = 0;

                if(this.selectedPreMaterials.material_type){
                    if(app.selectedPreMaterials.pre_practical_weight && app.selectedPreMaterials.pre_time_material && app.selectedPreMaterials.pre_practical_temperature && app.selectedPreMaterials.pre_practical_RPM){
                            variate_num += 1;
                            batching_details_list.push({
                            sn: variate_num,
                            material: app.selectedPreMaterials.material,
                            ratio_weight: app.selectedPreMaterials.pre_ratioVolume,
                            standard_volume: app.selectedPreMaterials.pre_calculateVolume,
                            actual_volume: app.selectedPreMaterials.pre_practicalVolume,
                            standard_weight: app.selectedPreMaterials.pre_calculateWeight,
                            actual_weight: app.selectedPreMaterials.pre_practical_weight,
                            time_interval: app.selectedPreMaterials.pre_time_material,
                            temperature: app.selectedPreMaterials.pre_practical_temperature,
                            rpm: app.selectedPreMaterials.pre_practical_RPM,
                            previous_product_batching:app.selectedPreMaterials.previous_product_batching,
                        })
                    }
                    else {
                        app.$message({
                            message: "上段次必填数据不能为空",
                            type: 'error'
                        });
                        return
                    }

                }

                for (var i = 0; i < this.ProductRecipe.length; ++i) {
                    if(app.ProductRecipe[i].calculateWeight && app.ProductRecipe[i].time_material && app.ProductRecipe[i].practical_temperature && app.ProductRecipe[i].practical_RPM){
                        variate_num += 1;
                        var now_stage_material = {
                            sn: variate_num,
                            material: app.ProductRecipe[i].material,
                            ratio_weight: app.ProductRecipe[i].ratioVolume,
                            standard_volume: app.ProductRecipe[i].calculateVolume,
                            actual_volume: app.ProductRecipe[i].practicalVolume,
                            standard_weight: app.ProductRecipe[i].calculateWeight,
                            actual_weight: app.ProductRecipe[i].practical_weight,
                            time_interval: app.ProductRecipe[i].time_material,
                            temperature: app.ProductRecipe[i].practical_temperature,
                            rpm: app.ProductRecipe[i].practical_RPM,
                        };
                        batching_details_list.push(now_stage_material);
                    }
                    else {
                        app.$message({
                            message: "本段次必填数据不能为空",
                            type: 'error'
                        });
                        return
                    }
                }

                if(app.discharge_time_material){
                }
                else {
                    app.$message({
                        message: "炼胶时间不能为空",
                        type: 'error'
                    });
                    return
                }

                if(app.select_rm_time_interval){
                    var variate_rm_time_interval = app.select_rm_time_interval
                }
                else {
                    variate_rm_time_interval = null
                }
                console.log('=================================================');
                console.log(app.select_rm_time_interval);
                console.log('=================================================');

                axios.post(RubberMaterialUrl, {
                    product_info: app.rubberMaterialForm['stage_product_batch_no'],
                    stage_product_batch_no: app.select_stage_product_batch_no,
                    stage: app.rubberMaterialForm['stage'],
                    dev_type: app.rubberMaterialForm['dev_type_name'],
                    batching_time_interval: app.discharge_time_material,
                    rm_time_interval: variate_rm_time_interval,
                    production_time_interval: app.discharge_time_material,
                    batching_details: batching_details_list,
                }).then(function (response) {

                    app.dialogChoiceMaterials = false;
                    app.$message(app.select_stage_product_batch_no + "保存成功");
                    app.currentChange(app.currentPage);

                }).catch(function (error) {
                    app.$message({
                        message: error.response.data,
                        type: 'error'
                    });
                });

            },

            put_saveMaterialClicked: function () {
                var app = this;
                var batching_details_list = [];

                for (var i = 0; i < this.PutProductRecipe.length; ++i) {
                    if(app.PutProductRecipe[i].standard_weight && app.PutProductRecipe[i].time_interval && app.PutProductRecipe[i].temperature && app.PutProductRecipe[i].rpm){
                        var now_stage_material = {
                            id: app.PutProductRecipe[i].id,
                            sn: app.PutProductRecipe[i].sn,
                            material: app.PutProductRecipe[i].material,
                            material_type: app.PutProductRecipe[i].material_type,
                            material_name: app.PutProductRecipe[i].material_name,
                            ratio: app.PutProductRecipe[i].ratio,
                            density: app.PutProductRecipe[i].density,
                            ratio_weight: app.PutProductRecipe[i].ratio_weight,
                            standard_volume: app.PutProductRecipe[i].standard_volume,
                            actual_volume: app.PutProductRecipe[i].actual_volume,
                            standard_weight: app.PutProductRecipe[i].standard_weight,
                            actual_weight: app.PutProductRecipe[i].actual_weight,
                            time_interval: app.PutProductRecipe[i].time_interval,
                            temperature: app.PutProductRecipe[i].temperature,
                            rpm: app.PutProductRecipe[i].rpm,
                            previous_product_batching:app.PutProductRecipe[i].previous_product_batching,
                        };
                        batching_details_list.push(now_stage_material);
                    }else{
                        app.$message({
                            message: "必填字段不能为空",
                            type: 'error'
                        });
                        return
                    }

                }


                if(app.put_discharge_time_material){
                }
                else {
                    app.$message({
                        message: "炼胶时间不能为空",
                        type: 'error'
                    });
                    return
                }

                if(app.put_select_rm_time_interval){
                    var variate_put_rm_time_interval = app.put_select_rm_time_interval
                }
                else {
                    variate_put_rm_time_interval = null
                }


                axios.put(RubberMaterialUrl + this.currentRow.id + "/", {
                    rm_time_interval: variate_put_rm_time_interval,
                    batching_time_interval: app.put_discharge_time_material,
                    production_time_interval: app.put_discharge_time_material,
                    batching_details:batching_details_list,
                }).then(function (response) {

                    app.dialogRubberMaterialStandard = false;
                    app.$message(app.put_select_stage_product_batch_no + "修改成功");
                    app.currentChange(app.currentPage);

                }).catch(function (error) {

                    app.$message({
                        message: error.response.data,
                        type: 'error'
                    });
                });

            },

            afterGetData: function () {

                this.currentRow = {
                    used_type: -1
                }
            },

            RmFlagFormatter: function(row, column) {

                return this.boolFormatter(row.rm_flag);
            },
            handleCurrentChange: function (val) {

                this.currentRow = val;
            },

        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount('#app')
})();
