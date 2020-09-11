;(function () {

    var Main = {

        mixins: [BaseMixin],
        data: function () {

            return {

                tableDataUrl: GlobalTypesUrl,
                type_name: '',
                globalCodeTypesCurrentRow: null,
                dialogCreateGlobalCodeTypeVisible: false,
                dialogEditGlobalCodeTypeVisible: false,
                globalCodeTypeForm: {

                    type_no: '',
                    type_name: '',
                    description: '',
                    use_flag: true
                },
                globalCodeTypeFormError: {},

                globalCodes: [],
                dialogCreateGlobalCodeVisible: false,
                dialogEditGlobalCodeVisible: false,
                globalCodeForm: {

                    global_no: '',
                    global_name: '',
                    description: '',
                    use_flag: true,
                    global_type: null
                },
                globalCodeFormError: {}
            }
        },
        methods: {

            beforeGetData: function () {

                this.getParams['type_name'] = this.type_name;
            },
            afterGetData: function () {

                console.log(this.tableData, 'tableData')
                this.globalCodeTypesCurrentRow = null;
            },
            typeNameChanged: function () {  // 类型名搜索

                this.getFirstPage();
            },
            clearGlobalCodeTypeForm: function () {

                this.globalCodeTypeForm = {
                    type_no: '',
                    type_name: '',
                    description: '',
                    use_flag: true
                };
            },
            clearGlobalCodeTypeFormError: function () {

                this.globalCodeTypeFormError = {
                    type_no: '',
                    type_name: '',
                    description: '',
                    use_flag: ''
                };
            },
            showCreateGlobalCodeTypeDialog: function () {

                this.clearGlobalCodeTypeForm();
                this.clearGlobalCodeTypeFormError();
                this.dialogCreateGlobalCodeTypeVisible = true;
            },
            handleCreateGlobalCodeType: function () { // 创建全局代码类型

                this.clearGlobalCodeTypeFormError();
                const app = this;
                axios.post(GlobalTypesUrl, this.globalCodeTypeForm)
                    .then(function (response) {

                        app.dialogCreateGlobalCodeTypeVisible = false;
                        app.$message(app.globalCodeTypeForm.type_name + "创建成功");
                        app.currentChange(app.currentPage);
                    }).catch(function (error) {

                    for (var key in app.globalCodeTypeFormError) {
                        if (error.response.data[key])
                            app.globalCodeTypeFormError[key] = error.response.data[key].join(",")
                    }
                });
            },
            showEditGlobalCodeTypeDialog: function (row) {

                this.clearGlobalCodeTypeForm();
                this.clearGlobalCodeTypeFormError();
                this.globalCodeTypeForm = Object.assign({}, row);
                this.dialogEditGlobalCodeTypeVisible = true;
            },
            handleEditGlobalCodeType: function () {

                const app = this;
                axios.put(GlobalTypesUrl + this.globalCodeTypeForm.id + '/', this.globalCodeTypeForm)
                    .then(function (response) {

                        app.dialogEditGlobalCodeTypeVisible = false;
                        app.$message(app.globalCodeTypeForm.type_name + "修改成功");
                        app.currentChange(app.currentPage);
                    }).catch(function (error) {
                    for (var key in app.globalCodeTypeFormError) {

                        if (error.response.data[key])
                            app.globalCodeTypeFormError[key] = error.response.data[key].join(",")
                    }
                });
            },
            handleGlobalCodeTypeDelete: function (row) {

                var app = this;
                this.$confirm('此操作将永久删除' + row.type_name + ', 是否继续?', '提示', {
                    confirmButtonText: '确定',
                    cancelButtonText: '取消',
                    type: 'warning'
                }).then(function () {

                    axios.delete(GlobalTypesUrl + row.id + '/')
                        .then(function (response) {
                            app.$message({
                                type: 'success',
                                message: '删除成功!'
                            });
                            if (app.tableData.length === 1 && app.currentPage > 1) {
                                --app.currentPage;
                            }
                            app.currentChange(app.currentPage);
                        }).catch(function (error) {

                        app.$message.error(error);
                    });


                }).catch(function () {

                });
            },

            handleGlobalCodeTypesCurrentRowChange: function (row) {

                if (!row)
                    return;
                var app = this;
                this.globalCodeTypesCurrentRow = row;
                axios.get(GlobalCodesUrl, {
                    params: {
                        id: row.id
                    }
                }).then(function (response) {

                    app.globalCodes = response.data.results;
                    app.globalCodeForm.global_type = row.id;
                }).catch(function (error) {

                    this.$message.error(error);
                })
            },
            clearGlobalCodeForm: function () {

                this.globalCodeForm = {

                    global_no: '',
                    global_name: '',
                    description: '',
                    use_flag: true,
                    global_type: this.globalCodeForm.global_type
                };
            },
            clearGlobalCodeFormError: function () {

                this.globalCodeFormError = {

                    global_no: '',
                    global_name: '',
                    description: '',
                    use_flag: '',
                }
            },
            showCreateGlobalCodeDialog: function () {

                if (!this.globalCodeForm.global_type)
                    return;
                this.clearGlobalCodeForm();
                this.clearGlobalCodeFormError();
                this.dialogCreateGlobalCodeVisible = true
            },
            handleCreateGlobalCode: function () {

                this.clearGlobalCodeFormError();
                // this.globalCodeForm.use_flag = this.globalCodeForm.used_flag_b ? 0 : 1;
                var app = this;
                axios.post(GlobalCodesUrl, this.globalCodeForm)
                    .then(function (response) {

                        app.dialogCreateGlobalCodeVisible = false;
                        app.$message(app.globalCodeForm.global_name + "创建成功");
                        app.handleGlobalCodeTypesCurrentRowChange(app.globalCodeTypesCurrentRow);
                    }).catch(function (error) {

                    for (var key in app.globalCodeFormError) {
                        if (error.response.data[key])
                            app.globalCodeFormError[key] = error.response.data[key].join(",")
                    }
                });
            },
            showEditGlobalCodeDialog: function (row) {

                this.clearGlobalCodeForm();
                this.clearGlobalCodeFormError();
                this.globalCodeForm.id = row.id;
                this.globalCodeForm.global_no = row.global_no;
                this.globalCodeForm.global_name = row.global_name;
                this.globalCodeForm.description = row.description;
                this.globalCodeForm.use_flag = row.use_flag;
                this.dialogEditGlobalCodeVisible = true;
            },
            handleEditGlobalCode: function () {

                // this.globalCodeForm.use_flag = this.globalCodeForm.used_flag_b ? 0 : 1;
                console.log(this.globalCodeForm, 'this.globalCodeForm')
                const app = this;
                axios.put(GlobalCodesUrl + this.globalCodeForm.id + '/', this.globalCodeForm)
                    .then(function (response) {

                        app.dialogEditGlobalCodeVisible = false;
                        app.$message(app.globalCodeForm.global_name + "修改成功");
                        app.handleGlobalCodeTypesCurrentRowChange(app.globalCodeTypesCurrentRow);
                    }).catch(function (error) {
                    for (var key in app.globalCodeFormError) {

                        for (var key in app.globalCodeFormError) {
                            if (error.response.data[key])
                                app.globalCodeFormError[key] = error.response.data[key].join(",")
                        }
                    }
                    app.$message.error(error.response.data['global_type'].join(","));
                });
            },
            handleGlobalCodesDelete: function (row) {

                var app = this;
                this.$confirm('此操作将永久删除' + row.global_name + ', 是否继续?', '提示', {
                    confirmButtonText: '确定',
                    cancelButtonText: '取消',
                    type: 'warning'
                }).then(function () {

                    axios.delete(GlobalCodesUrl + row.id + '/')
                        .then(function (response) {
                            app.$message({
                                type: 'success',
                                message: '删除成功!'
                            });
                            app.handleGlobalCodeTypesCurrentRowChange(app.globalCodeTypesCurrentRow);
                        }).catch(function (error) {

                        app.$message.error(error);
                    });


                }).catch(function () {

                });
            },
            globalCodeTypeFormatter: function (row, column) {

                return this.boolFormatter(row.use_flag);
            },
            globalCodeUsedFlagFormatter: function (row, column) {

                return this.boolFormatter(row.use_flag);
            },
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount('#app')

})
();