;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {

                tableDataUrl: ProductActualUrl,
                tableData: [
                    {
                        material_type: "01",
                        material_no: "aaa-mm-01",
                        standard_weight: 123,
                        daily_plan: 123,
                        daily_result: 123,
                        class: {
                            morning_shift: {
                                plan: 11,
                                result:22
                            },
                            middle_shift: {
                                plan: 11,
                                result:22
                            },
                            night_shift: {
                                plan: 11,
                                result:22
                            },
                        }
                    },
                    {
                        material_type: "01",
                        material_no: "aaa-mm-01",
                        standard_weight: 123,
                        daily_plan: 123,
                        daily_result: 123,
                        class: {
                            morning_shift: {
                                plan: 11,
                                result:22
                            },
                            middle_shift: {
                                plan: 11,
                                result:22
                            },
                            night_shift: {
                                plan: 11,
                                result:22
                            },
                        }
                    },
                    {
                        material_type: "01",
                        material_no: "aaa-mm-01",
                        standard_weight: 123,
                        daily_plan: 123,
                        daily_result: 123,
                        class: {
                            morning_shift: {
                                plan: 11,
                                result:22
                            },
                            middle_shift: {
                                plan: 11,
                                result:22
                            },
                            night_shift: {
                                plan: 11,
                                result:22
                            },
                        }
                    }
                ],
                performanceDate: Date.now(),
                projectName: "",
                machineNo: "",
                machineNoOptions: [],
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
                },
                outerVisible: false,
                innerVisible: false
            }
        },
        created: function () {

            var app = this;
            axios.get(GlobalCodesUrl, {

                params: {

                    class_name: "机台"
                }
            }).then(function (response) {

                app.machineNoOptions = response.data.results;
            }).catch(function (error) {

            });
            console.log(app.tableData);
        },
        methods: {
            detailsClick(rew) {
            },
            downloadClick(rew) {
            },
            materialNameChanged() {
                this.getFirstPage();
            },
            machineNoChange() {
                this.getFirstPage();
            },
            showAddDialog() {
            },
            // currentChange() {
            // },
            // beforeGetData() {
            //
            //     this.getParams["material_id"] = this.materialType
            // },
        //
        //     materialTypeChange: function () {
        //
        //         this.getFirstPage();
        //     },
        //
        //     showAddDialog: function () {
        //
        //         this.clearMaterialBaseInfoForm();
        //         this.dialogAddMaterialBaseInfoVisible = true
        //     },
        //     clearMaterialBaseInfoForm() {
        //
        //         this.materialBaseInfoForm = {
        //
        //             material_no: "",
        //             material_name: "",
        //             for_short: "",
        //             density: null,
        //             used_flag: false,
        //             material_type: null,
        //             package_unit: null
        //         };
        //     },
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();