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
                dialogAddMaterialBaseInfoVisible: false,
                dialogEditMaterialBaseInfoVisible: false,
                packingUnitOptions: [],
                materialBaseInfoForm: {

                    // material_no: "",
                    // material_name: "",
                    // for_short: "",
                    // density: null,
                    // used_flag: false,
                    // material_type: null,
                    // package_unit: null
                },
                materialBaseInfoFormError: {

                    // material_no: "",
                    // material_name: "",
                    // for_short: "",
                    // density: "",
                    // used_flag: "",
                    // material_type: "",
                    // package_unit: ""
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
            showAddMaterialDialog: function () {

                this.clearMaterialBaseInfoForm();
                this.dialogAddMaterialBaseInfoVisible = true
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

        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount('#app')
})();