;(function () {

    var Main = {

        mixins: [BaseMixin, Equip_cate_filter],
        data: function () {

            return {
                dialogCreateEquipCateVisible: false,
                tableDataUrl: EquipCategoryUrl,

                EquipCate: [],
                EquipCateOptions: [],
                equip_type: "",

                EquipCateProcess: [],
                EquipCateProcessOptions: [],
                process: "",

                EquipCateForm: {
                    category_no: "",
                    category_name: "",
                    volume: "",
                    equip_type: "",
                    process: "",
                },
                equipcate_rules: {
                    category_no: [{ required: true, message: '请输入机型编号', trigger: 'blur' }],
                    category_name: [{ required: true, message: '请输入机型名称', trigger: 'blur' }],
                    volume: [{ required: true, message: '请输入容积', trigger: 'blur' }],
                    equip_type: [{ required: true, message: '请选择设备类型', trigger: 'change' }],
                    process: [{ required: true, message: '请选择工序', trigger: 'change' }],
                },
                EquipCateFormError: {
                    category_no: "",
                    category_name: "",
                    volume: "",
                    equip_type: "",
                    process: "",
                },
                dialogEditEquipCateVisible: false,
            }
        },
        methods: {

            shiftsEquipCateChange() {

            },
            shiftsEquipCateProcessChange() {

            },

            clearEquipCateForm: function () {

                this.EquipCateForm = {
                    category_no: "",
                    category_name: "",
                    volume: "",
                    equip_type: "",
                    process: "",
                }
            },
            clearEquipCateFormError: function () {

                this.EuqipCateFormError = {
                    category_no: "",
                    category_name: "",
                    volume: "",
                    equip_type: "",
                    process: "",
                }
            },
            showCreateEquipCateDialog: function () {

                this.clearEquipCateForm();
                this.clearEquipCateFormError();
                this.dialogCreateEquipCateVisible = true;
            },
            handleCreateEquipCate(formName){
                var app = this;
                app.$refs[formName].validate((valid) => {
                  if (valid) {
                      this.clearEquipCateFormError();
                      var app = this;
                      axios.post(EquipCategoryUrl, app.EquipCateForm)
                          .then(function (response) {

                              app.dialogCreateEquipCateVisible = false;
                              app.$message(app.EquipCateForm.category_name + "创建成功");
                              app.currentChange(app.currentPage);

                          }).catch(function (error) {

                          for (var key in app.EquipCateFormError) {
                              if (error.response.data[key])
                                  app.EquipCateFormError[key] = error.response.data[key].join(",")
                          }
                      })
                  }else {
                    console.log('error submit!!');
                    return false;
                  }
                });
            },
            showEditEquipCateDialog: function (row) {
                this.clearEquipCateForm();
                this.clearEquipCateFormError();
                this.EquipCateForm = Object.assign({}, row);
                console.log("=============================");
                console.log(this.EquipCateForm);
                console.log("=============================");
                this.dialogEditEquipCateVisible = true;
            },


            handleEditEquipCate(formName) {
                var app = this;
                app.$refs[formName].validate((valid) => {
                  if (valid) {
                            const app = this;
                            axios.put(EquipCategoryUrl + this.EquipCateForm.id + '/', this.EquipCateForm)
                                .then(function (response) {

                                    app.dialogEditEquipCateVisible = false;
                                    app.$message(app.EquipCateForm.category_name + "修改成功");
                                    app.currentChange(app.currentPage);
                                }).catch(function (error) {
                                for (var key in app.EquipCateFormError) {

                                    if (error.response.data[key])
                                        app.EquipCateFormError[key] = error.response.data[key].join(",")
                                }
                            });
                  }else {
                    console.log('error submit!!');
                    return false;
                  }
                });
            },
            handleEquipCateDelete: function (row) {

                var app = this;
                this.$confirm('此操作将永久删除' + row.category_name + ', 是否继续?', '提示', {
                    confirmButtonText: '确定',
                    cancelButtonText: '取消',
                    type: 'warning'
                }).then(() => {

                    axios.delete(EquipCategoryUrl + row.id + '/')
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


        },

        created: function () {

            var app = this;
            axios.get(EquipTypeGlobalUrl)
                .then(function (response) {

                    app.EquipCate = response.data.results;
                    // console.log("==================");
                    // console.log(app.EquipCate);
                    // console.log("==================");
                    for (var i = 0; i < app.EquipCate.length; ++i) {

                        var label = app.EquipCate[i]["global_name"];
                        app.EquipCateOptions.push({
                            value: app.EquipCate[i]["id"],
                            label
                        });
                    }
                }).catch(function (error) {

            });
            axios.get(EquipProcessGlobalUrl)
                .then(function (response) {

                    app.EquipCateProcess = response.data.results;
                    for (var i = 0; i < app.EquipCateProcess.length; ++i) {

                        var label = app.EquipCateProcess[i]["global_name"];
                        app.EquipCateProcessOptions.push({
                            value: app.EquipCateProcess[i]["id"],
                            label
                        });
                    }
                }).catch(function (error) {

            })
        }

    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();