;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {

                tableDataUrl: ProductActualUrl,
                performanceDate: dayjs("2020-08-07").format("YYYY-MM-DD"),
                projectName: "",
                equipNo: "",
                equipNoOptions: [],
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
                dialogVisibleRubber: false,
                tableDataRubber: [],
                tableDataBAT:[],
                dialogVisibleBAT: false
            }
        },
        created: function () {

            var app = this;
            axios.get(GlobalCodesUrl, {

                params: {

                    class_name: "机台"
                }
            }).then(function (response) {

                app.equipNoOptions = response.data.results;
            }).catch(function (error) {

            });
            console.log(app.tableData);
        },
        methods: {
            downloadClick(rew) {
            },
            performanceDateChange() {
                this.getFirstPage();
            },
            materialNameChanged() {
                this.getFirstPage();
            },
            equipNoChange() {
                this.getFirstPage();
            },
            showAddDialog() {
            },
            currentChange: function (page) {

            this.beforeGetData();
            this.getParams["page"] = page;
            this.tableData = [];
            const app = this;
            axios.get(this.tableDataUrl, {

                params: this.getParams
            }).then(function (response) {

                if (app.tableDataTotal !== response.data.count) {
                    app.tableDataTotal = response.data.count;
                }
                app.tableData = response.data.data;
                app.afterGetData();

            }).catch(function (error) {
                // this.$message.error(error);
            })
            },
            beforeGetData() {
                console.log(this.planDate);
                this.getParams["search_time"] = dayjs(this.performanceDate).format("YYYY-MM-DD");
                this.getParams["equip_no"] = this.equipNo
            },
            detailsClick() {
                this.dialogVisibleRubber = true

            },
            clickBAT() {
                this.dialogVisibleBAT = true
            },
            viewGraph() {
            }
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