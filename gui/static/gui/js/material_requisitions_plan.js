;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {
                num1: 5,
                num2: 6,
                aaa: 10,
                tableDataUrl: MaterialRequisitions,
                planDate: Date.now(),
                materialType: "",
                material_name: "",
                planDateOptions: [],
                ClassesCount: [0, 1, 2],
                ClassesOptions: ["早班", "中班", "晚班"],
                materialTypeOptions: [],
                dialogEditVisible: false,
                editForm: {

                    id: "",
                    plan_date: "2020-09-09",
                    material_name: "",
                    weight: [
                        {
                            need_weight: 10,
                            plan_weight: 0,
                        },
                        {
                            need_weight: 20,
                            plan_weight: 0,
                        },
                        {
                            need_weight: 30,
                            plan_weight: 0,
                        }
                    ]
                },
                editFormError: {

                    id: "",
                    plan_date: "",
                    material_name: "",
                    weight: ""
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
            // console.log(this.tableData)
        },
        methods: {

            beforeGetData() {

                this.getParams["plan_data"] = this.planDate;
                this.getParams["material_type"] = this.materialType;
                this.getParams["material_name"] = this.material_name
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

                // this.clearEditFormError();
                // this.editForm.id = row.id;
                // this.editForm.plan_data = row.plan_data;
                // this.editForm.material_name = row.material_name;
                // this.editForm.weight = row.weight;
                this.dialogEditVisible = true;
            },

            saveRequisitionsPlan(editForm) {
                this.clearEditFormError();
                var app = this;
                this.$refs[formName].validate((valid) => {
                    if (valid) {

                        axios.put(MaterialRequisitions + app.editForm.id + '/', app.editForm)
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

                    id: "",
                    plan_date: "2020-09-09",
                    material_name: "",
                    weight: [
                        {
                            need_weight: 0,
                            plan_weight: 0,
                        },
                        {
                            need_weight: 0,
                            plan_weight: 0,
                        },
                        {
                            need_weight: 0,
                            plan_weight: 0,
                        }
                    ]
                };
            },
            clearEditFormError() {

                this.editFormError = {

                    id: "",
                    plan_date: "",
                    material_name: "",
                    weight: ""
                }
            },
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();