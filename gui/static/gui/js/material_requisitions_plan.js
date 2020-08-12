;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {
                num1: 5,
                num2: 6,
                aaa: 10,
                tableDataUrl: MaterialDemanded,
                planDate: "2020-08-07",
                materialType: "",
                material_name: "",
                planDateOptions: ["2020-08-07","2020-08-08","2020-08-09"],
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
                    page_size: 100000000
                }
            }).then(function (response) {

                app.planSchedules = response.data.results;
            }).catch(function (error) {

            });
            console.log(this.planDate)
        },
        methods: {

            beforeGetData() {
                console.log(this.planDate);
                this.getParams["plan_date"] = this.planDate;
                this.getParams["material_type"] = this.materialType;
                this.getParams["material_name"] = this.material_name
            },
            currentChange: function (page) {

                this.beforeGetData();
                console.log(this.getParams);
                this.getParams["page"] = page;
                this.tableData = [];
                const app = this;
                axios.get(this.tableDataUrl, {

                    params: this.getParams
                }).then(function (response) {
                    console.log(response.data);
                    if (app.tableDataTotal !== response.data.count) {
                        app.tableDataTotal = response.data.count;
                    }
                    app.tableData = response.data;

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

                this.clearEditFormError();
                console.log(row.material_demanded_list[0].id)
                this.editForm.material_ids.push(row.material_demanded_list[0].id);
                this.editForm.material_ids.push(row.material_demanded_list[1].id);
                this.editForm.material_ids.push(row.material_demanded_list[2].id);
                this.editForm.material_name = row.material_name
                this.editForm.plan_data = this.planDate;
                this.editForm.weights.push(row.md_material_requisition_classes[0].早);
                this.editForm.weights.push(row.md_material_requisition_classes[1].中);
                this.editForm.weights.push(row.md_material_requisition_classes[2].晚);
                this.dialogEditVisible = true;
            },

            saveRequisitionsPlan(editForm) {
                this.clearEditFormError();
                var app = this;
                this.$refs[editForm].validate((valid) => {
                    if (valid) {
                        console.log(app.editForm)
                        axios.post(MaterialRequisitions, app.editForm)
                            .then(function (response) {

                                app.dialogEditVisible = false;
                                app.$message(app.editForm.plan_data + app.editForm.material_name + "修改成功");
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