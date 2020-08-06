;(function () {

    var Main = {
        mixins: [BaseMixin, Rubber_Material_filter],
        data: function () {

            return {

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
                dialogAddRubberMaterial: false,

                rubberMaterialForm: {
                    factory: "",
                    stage_product_batch_no: "",
                    stage: "",
                    dev_type_name: "",
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
                        var label = app.PopupRubberSite[i]["global_name"];
                        app.PopupRubberSiteOptions.push({
                            value: app.PopupRubberSite[i]["id"],
                            label
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
                axios.get(RubberStageUrl + this.rubberMaterialForm['factory'], {}
                ).then(function (response) {
                    var ProductBatchNo = response.data;
                        for (var i = 0; i < ProductBatchNo.length; ++i) {
                            app.ProductBatchNoOptions.push({
                                value: ProductBatchNo[i]["product_info"],
                                label: ProductBatchNo[i]["product_no"],
                            });
                        }
                }).catch(function (error) {
                });
            },
            shiftsProductBatchNoChange(){
                var app = this;
                axios.get(RubberStageUrl + this.rubberMaterialForm['factory'], {}
                ).then(function (response) {
                    var Stage = response.data;
                    for (var i = 0; i < Stage.length; ++i) {
                        if(Stage[i]["product_info"] == app.rubberMaterialForm['stage_product_batch_no']){
                            for(var j = 0; j < Stage[i]['stages'].length; ++j){
                                app.StageOptions.push({
                                    value: Stage[i]['stages'][j]["stage"],
                                    label: Stage[i]['stages'][j]["stage__global_name"],
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
                this.dialogAddRubberMaterial = true;
                this.currentRow = null // 新建和更新标志
            },
            handleAddRubberMaterial: function () {

                var app = this;
                this.rubberMatetialError = "";
                axios.get(ValidateVersionsUrl, {

                }).then(function (response) {

                }).catch(function (error) {

                });
            },
            clearMaterialBaseInfoForm() {

                this.materialBaseInfoForm = {

                    material_no: "",
                    material_name: "",
                    for_short: "",
                    density: null,
                    used_flag: false,
                    material_type: null,
                    package_unit: null
                };
            },
            clearMaterialBaseInfoFormError() {

                this.materialBaseInfoFormError = {

                    material_no: "",
                    material_name: "",
                    for_short: "",
                    density: "",
                    used_flag: "",
                    material_type: "",
                    package_unit: ""
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