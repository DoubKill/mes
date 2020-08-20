;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {

                tableDataUrl: MaterialsUrl,
                materialType: "",
                materialTypeOptions: [],
                dialogAddMaterialBaseInfoVisible: false,
                dialogEditMaterialBaseInfoVisible: false,
                packingUnitOptions: [],
                materialBaseInfoForm: {

                    material_no: "",
                    material_name: "",
                    for_short: "",
                    // density: null,
                    used_flag: false,
                    material_type: null,
                    package_unit: null
                },
                materialBaseInfoFormError: {

                    material_no: "",
                    material_name: "",
                    for_short: "",
                    // density: "",
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
            axios.get(GlobalCodesUrl, {

                params: {

                    class_name: "包装单位"
                }
            }).then(function (response) {

                app.packingUnitOptions = response.data.results;
            }).catch(function (error) {

            });
        },
        methods: {

            formatter: function (row, column) {

                return row.used_flag ? "Y" : "N"
            },
            beforeGetData() {

                this.getParams["material_type_id"] = this.materialType
            },
            materialTypeChange: function () {

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
                    // density: null,
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
                    // density: "",
                    used_flag: "",
                    material_type: "",
                    package_unit: ""
                }
            },
            handleAddMaterialBaseInfo: function () {

                this.clearMaterialBaseInfoFormError();
                var app = this;
                axios.post(MaterialsUrl, app.materialBaseInfoForm)
                    .then(function (response) {

                        app.dialogAddMaterialBaseInfoVisible = false;
                        app.$message(app.materialBaseInfoForm.material_name + "创建成功");
                        app.currentChange(app.currentPage);
                    }).catch(function (error) {

                    for (const key in app.materialBaseInfoFormError) {
                        if (error.response.data[key])
                            app.materialBaseInfoFormError[key] = error.response.data[key].join(",")
                    }
                })
            },
            showEditMaterialDialog(row) {

                this.clearMaterialBaseInfoFormError();
                this.materialBaseInfoForm = Object.assign({}, row);
                this.dialogEditMaterialBaseInfoVisible = true
            },
            handleMaterialDelete(row) {

                var app = this;
                this.$confirm('此操作将永久删除' + row.material_name + ', 是否继续?', '提示', {
                    confirmButtonText: '确定',
                    cancelButtonText: '取消',
                    type: 'warning'
                }).then(() => {

                    axios.delete(MaterialsUrl + row.id + '/')
                        .then(function (response) {
                            app.$message({
                                type: 'success',
                                message: '删除成功!'
                            });
                            app.currentChange(app.currentPage);
                        }).catch(function (error) {

                        app.$message.error(error);
                    });


                }).catch(() => {

                });
            },
            handleEditMaterialBaseInfo() {

                this.clearMaterialBaseInfoFormError();
                var app = this;
                axios.put(MaterialsUrl + app.materialBaseInfoForm.id + "/", app.materialBaseInfoForm)
                    .then(function (response) {

                        app.dialogEditMaterialBaseInfoVisible = false;
                        app.$message(app.materialBaseInfoForm.material_name + "修改成功");
                        app.currentChange(app.currentPage);
                    }).catch(function (error) {

                    for (const key in app.materialBaseInfoFormError) {
                        if (error.response.data[key])
                            app.materialBaseInfoFormError[key] = error.response.data[key].join(",")
                    }
                })
            }
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount('#app')
})();