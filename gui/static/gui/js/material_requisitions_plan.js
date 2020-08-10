;(function () {
    // 复制领料日计划接口
    const MaterialRequisitionsCopy = "/api/v1/plan/material-requisitions-copy/";

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {

                tableDataUrl: MaterialRequisitions,
                planDate: Date.now(),
                materialType: "",
                aaa: '10',
                planDateOptions: [],
                ClassesCount: [0, 1, 2],
                ClassesOptions: ["早班", "中班", "晚班"],
                materialTypeOptions: [],
                dialogAddMaterialBaseInfoVisible: false,
                materialBaseInfoForm: {

                    material_no: "",
                    material_name: "",
                    for_short: "",
                    density: null,
                    used_flag: false,
                    material_type: null,
                    package_unit: null
                },
                materialBaseInfoFormError: {

                    material_no: "",
                    material_name: "",
                    for_short: "",
                    density: "",
                    used_flag: "",
                    material_type: "",
                    package_unit: ""
                }
            }
        },
        created: function () {

            var app = this;
            axios.get(GlobalCodesUrl, {

                params: {

                    class_name: "原材料类别"
                }
            }).then(function (response) {

                app.materialTypeOptions = response.data.results;
            }).catch(function (error) {

            });
            // const  date = dayjs(this.planDate);
            console.log(this.planDate)
        },
        methods: {

            beforeGetData() {

                this.getParams["material_id"] = this.materialType
            },

            materialTypeChange: function () {

                this.getFirstPage();
            },

            showAddDialog: function () {

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
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();