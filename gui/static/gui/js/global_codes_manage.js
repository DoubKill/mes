;(function () {

    var Main = {

        mixins: [mixin],
        data() {

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
                    used_flag: true
                },
                globalCodeTypeFormError: {},

                globalCodes: [],
                dialogCreateGlobalCodeVisible: false,
                dialogEditGlobalCodeVisible: false,
                globalCodeForm: {

                    global_no: '',
                    global_name: '',
                    description: '',
                    used_flag_b: true,
                    used_flag: 0, // 0用
                    global_type: null
                },
                globalCodeFormError: {}
            }
        },
        methods: {

            beforeGetData() {

                this.getParams['type_name'] = this.type_name;
            },
            afterGetData() {

                this.globalCodeTypesCurrentRow = null;
            },
            typeNameChanged() {  // 类型名搜索

                this.currentPage = 1;
                this.currentChange(1);
            },
            clearGlobalCodeTypeForm() {

                this.globalCodeTypeForm = {
                    type_no: '',
                    type_name: '',
                    description: '',
                    used_flag: true
                };
            },
            clearGlobalCodeTypeFormError() {

                this.globalCodeTypeFormError = {
                    type_no: '',
                    type_name: '',
                    description: '',
                    used_flag: ''
                };
            },
            showCreateGlobalCodeTypeDialog() {

                this.clearGlobalCodeTypeForm();
                this.clearGlobalCodeTypeFormError();
                this.dialogCreateGlobalCodeTypeVisible = true;
            },
            handleCreateGlobalCodeType() { // 创建全局代码类型

                this.clearGlobalCodeTypeFormError();
                const app = this;
                axios.post(GlobalTypesUrl, this.globalCodeTypeForm)
                    .then(function (response) {

                        app.dialogCreateGlobalCodeTypeVisible = false;
                        app.$message(app.globalCodeTypeForm.type_name + "创建成功");
                        app.currentChange(app.currentPage);
                    }).catch(function (error) {

                    for (const key in app.globalCodeTypeFormError) {
                        if (error.response.data[key])
                            app.globalCodeTypeFormError[key] = error.response.data[key].join(",")
                    }
                });
            },
            showEditGlobalCodeTypeDialog(row) {

                this.clearGlobalCodeTypeForm();
                this.clearGlobalCodeTypeFormError();
                this.globalCodeTypeForm = Object.assign({}, row);
                this.dialogEditGlobalCodeTypeVisible = true;
            },
            handleEditGlobalCodeType() {

                const app = this;
                axios.put(GlobalTypesUrl + this.globalCodeTypeForm.id + '/', this.globalCodeTypeForm)
                    .then(function (response) {

                        app.dialogEditGlobalCodeTypeVisible = false;
                        app.$message(app.globalCodeTypeForm.type_name + "修改成功");
                        app.currentChange(app.currentPage);
                    }).catch(function (error) {
                    for (const key in app.globalCodeTypeFormError) {

                        if (error.response.data[key])
                            app.globalCodeTypeFormError[key] = error.response.data[key].join(",")
                    }
                });
            },
            handleGlobalCodeTypeDelete(row) {

                var app = this;
                this.$confirm('此操作将永久删除' + row.type_name + ', 是否继续?', '提示', {
                    confirmButtonText: '确定',
                    cancelButtonText: '取消',
                    type: 'warning'
                }).then(() => {

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


                }).catch(() => {

                });
            },

            handleGlobalCodeTypesCurrentRowChange(row) {

                if (!row)
                    return;
                var app = this;
                this.globalCodeTypesCurrentRow = row;
                axios.get(GlobalCodesUrl, {
                    params: {
                        global_type_id: row.id
                    }
                }).then(function (response) {

                    app.globalCodes = response.data;
                    app.globalCodes.used_flag_b = app.globalCodes.used_flag ? 0 : 1;
                    app.globalCodeForm.global_type = row.id;
                }).catch(function (error) {

                    this.$message.error(error);
                })
            },
            clearGlobalCodeForm() {

                this.globalCodeForm = {

                    global_no: '',
                    global_name: '',
                    description: '',
                    used_flag_b: true,
                    used_flag: 0,
                    global_type: this.globalCodeForm.global_type
                };
            },
            clearGlobalCodeFormError() {

                this.globalCodeFormError = {

                    global_no: '',
                    global_name: '',
                    description: '',
                    used_flag: '',
                }
            },
            showCreateGlobalCodeDialog() {

                if (!this.globalCodeForm.global_type)
                    return;
                this.clearGlobalCodeForm();
                this.clearGlobalCodeFormError();
                this.dialogCreateGlobalCodeVisible = true
            },
            handleCreateGlobalCode() {

                this.clearGlobalCodeFormError();
                this.globalCodeForm.used_flag = this.globalCodeForm.used_flag_b ? 0 : 1;
                var app = this;
                axios.post(GlobalCodesUrl, this.globalCodeForm)
                    .then(function (response) {

                        app.dialogCreateGlobalCodeVisible = false;
                        app.$message(app.globalCodeForm.global_name + "创建成功");
                        app.handleGlobalCodeTypesCurrentRowChange(app.globalCodeTypesCurrentRow);
                    }).catch(function (error) {

                    for (const key in app.globalCodeFormError) {
                        if (error.response.data[key])
                            app.globalCodeFormError[key] = error.response.data[key].join(",")
                    }
                });
            },
            showEditGlobalCodeDialog(row) {

                this.clearGlobalCodeForm();
                this.clearGlobalCodeFormError();
                this.globalCodeForm.id  = row.id;
                this.globalCodeForm.global_no = row.global_no;
                this.globalCodeForm.global_name = row.global_name;
                this.globalCodeForm.description = row.description;
                this.globalCodeForm.used_flag_b = row.used_flag === 0;
                this.dialogEditGlobalCodeVisible = true;
            },
            handleEditGlobalCode() {

                this.globalCodeForm.used_flag = this.globalCodeForm.used_flag_b ? 0 : 1;
                const app = this;
                axios.put(GlobalCodesUrl + this.globalCodeForm.id + '/', this.globalCodeForm)
                    .then(function (response) {

                        app.dialogEditGlobalCodeVisible = false;
                        app.$message(app.globalCodeForm.global_name + "修改成功");
                        app.handleGlobalCodeTypesCurrentRowChange(app.globalCodeTypesCurrentRow);
                    }).catch(function (error) {
                    for (const key in app.globalCodeFormError) {

                        for (const key in app.globalCodeFormError) {
                            if (error.response.data[key])
                                app.globalCodeFormError[key] = error.response.data[key].join(",")
                        }
                    }
                });
            },
            handleGlobalCodesDelete(row) {

                var app = this;
                this.$confirm('此操作将永久删除' + row.global_name + ', 是否继续?', '提示', {
                    confirmButtonText: '确定',
                    cancelButtonText: '取消',
                    type: 'warning'
                }).then(() => {

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


                }).catch(() => {

                });
            },
            globalCodeTypeFormatter(row, column) {

                return this.boolFormatter(row.used_flag);
            },
            globalCodeUsedFlagFormatter(row, column) {

                return this.boolFormatter(row.used_flag === 0);
            },
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount('#app')

})
();