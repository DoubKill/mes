;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {
                num1: 5,
                num2: 6,
                aaa: 10,
                tableDataUrl: MaterialDemanded,
                planDate: dayjs().format("YYYY-MM-DD"),
                materialType: "",
                materialName: "",
                planDateOptions: [],
                ClassesCount: [0, 1, 2],
                ClassesOptions: ["早班", "中班", "晚班"],
                materialTypeOptions: [],
                dialogEditVisible: false,
                editForm: {

                    material_ids: [],
                    material_name:"",
                    plan_date: "",
                    weights: []
                },
                editFormError: {
                    material_ids: "",
                    plan_date: "",
                    weights: ""
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
            axios.get(PlanScheduleUrl, {

                params: {
                    all: 1
                }
            }).then(function (response) {

                app.planDateOptions = response.data.results;
            }).catch(function (error) {

            });
            this.currentChange(1)
            console.log(this.tableData, "this.tableData")
        },
        methods: {

            beforeGetData() {
                this.getParams["plan_date"] = this.planDate;
                this.getParams["material_type"] = this.materialType;
                this.getParams["material_name"] = this.materialName
            },
            currentChange: function (page) {

                this.beforeGetData();
                this.getParams["page"] = page;
                console.log(this.tableData, '1111111111111')
                this.tableData = [];
                console.log(this.tableData, '2222222222222')
                const app = this;
                axios.get(this.tableDataUrl, {

                    params: this.getParams
                }).then(function (response) {
                    if (app.tableDataTotal !== response.data.count) {
                        app.tableDataTotal = response.data.count;
                    }
                    console.log(response.results, "response.results")
                    app.tableData = response.results;
                    console.log(app.tableData, "app.tableData")
                    app.afterGetData();

                }).catch(function (error) {
                    app.$message.error(error);
                })
            },

            planDateChange: function () {

                this.getFirstPage();
            },

            materialTypeChange: function () {

                this.getFirstPage();
            },

            materialNameChanged: function () {

                this.getFirstPage();
            },

            showEditDialog(row) {

                this.clearEditForm();
                this.editForm.material_ids.push(row.material_demanded_list[0].id);
                this.editForm.material_ids.push(row.material_demanded_list[1].id);
                this.editForm.material_ids.push(row.material_demanded_list[2].id);
                this.editForm.material_name = row.material_name
                this.editForm.plan_date = this.planDate;
                if (row.md_material_requisition_classes[0]){
                    this.editForm.weights.push(row.md_material_requisition_classes[0].早班);
                    this.editForm.weights.push(row.md_material_requisition_classes[1].中班);
                    this.editForm.weights.push(row.md_material_requisition_classes[2].晚班);
                  }
                else {
                    this.editForm.weights.push(0);
                    this.editForm.weights.push(0);
                    this.editForm.weights.push(0);
                }
                this.dialogEditVisible = true;
                console.log(this.editForm)
            },

            saveRequisitionsPlan(editForm) {
                this.clearEditFormError();
                var app = this;
                this.$refs[editForm].validate((valid) => {
                    if (valid) {
                        axios.post(MaterialRequisitions, app.editForm)
                            .then(function (response) {

                                app.dialogEditVisible = false;
                                app.$message(app.editForm.plan_date + " " + app.editForm.material_name + " " + "修改成功");
                                app.currentChange(app.currentPage);

                            }).catch(function (error) {

                            // for (const key in app.editFormError) {
                            //     if (error.response.data[key])
                            //         app.editFormError[key] = error.response.data[key].join(",")
                            // }
                        })

                    } else {

                        return false;
                    }
                });
            },

            clearEditForm() {

                this.editForm = {

                    material_ids: [],
                    material_name:"",
                    plan_date: "",
                    weights: []
                };
            },
            clearEditFormError() {

                this.editFormError = {

                    material_ids: "",
                    plan_date: "",
                    weights: ""
                }
            },
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();